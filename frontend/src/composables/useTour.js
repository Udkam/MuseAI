import { computed, ref } from 'vue'
import { api } from '../api/index.js'
import { BANPO_PERSONA_BY_CODE, getHallDisplayName, mergeHallsWithContract } from '../constants/banpo.js'
import { useAuth } from './useAuth.js'
import { useTourWorkbench } from './useTourWorkbench.js'
import { useTTSPlayer } from './useTTSPlayer.js'

const tourSession = ref(null)
const sessionToken = ref(null)
const tourStep = ref('onboarding')
const currentHall = ref(null)
const currentExhibit = ref(null)
const hallExhibits = ref([])
const exhibitIndex = ref(0)
const streamingContent = ref('')
const suggestedActions = ref(null)
const chatMessages = ref([])
const loading = ref({ session: false, chat: false, report: false })
const error = ref(null)
const tourReport = ref(null)
const halls = ref([])

let eventBuffer = []
let eventFlushTimer = null
let exhibitStartTime = null

const EVENT_FLUSH_INTERVAL = 30000

const STORAGE_KEY_SESSION = 'tour_session_id'
const STORAGE_KEY_TOKEN = 'tour_session_token'
const STORAGE_KEY_EVENTS = 'tour_pending_events'

function buildHallWelcome(hallSlug) {
  const hallName = getHallDisplayName(hallSlug)
  return `欢迎来到${hallName}。你可以先告诉我想观察什么，也可以打开展品速览，围绕具体展品继续提问。`
}

function _getToken() {
  return sessionToken.value || null
}

function _persistSession() {
  if (tourSession.value) {
    localStorage.setItem(STORAGE_KEY_SESSION, tourSession.value.id)
    localStorage.setItem(STORAGE_KEY_TOKEN, sessionToken.value || '')
  }
}

function _persistEvents() {
  localStorage.setItem(STORAGE_KEY_EVENTS, JSON.stringify(eventBuffer))
}

export function useTour() {
  const { isAuthenticated, user } = useAuth()
  const { ttsPreferences } = useTourWorkbench()
  const { isPlaying: ttsPlaying, feedChunk, stop: stopTTS } = useTTSPlayer()

  async function createTourSession(interestType, persona, assumption) {
    loading.value.session = true
    error.value = null
    const guestId = isAuthenticated.value ? null : `guest-${crypto.randomUUID()}`
    const result = await api.tour.createSession({
      interest_type: interestType,
      persona,
      assumption,
      guest_id: guestId,
    })
    loading.value.session = false

    if (!result.ok) {
      error.value = result.data?.detail || '创建导览会话失败'
      return null
    }

    tourSession.value = result.data
    sessionToken.value = result.data.session_token
    _persistSession()

    const updateResult = await api.tour.updateSession(
      result.data.id,
      { status: 'opening', interest_type: interestType, persona, assumption },
      sessionToken.value,
    )
    if (updateResult?.ok) {
      tourSession.value = updateResult.data
    }
    return tourSession.value
  }

  async function restoreSession() {
    const storedId = localStorage.getItem(STORAGE_KEY_SESSION)
    const storedToken = localStorage.getItem(STORAGE_KEY_TOKEN)
    if (!storedId) return false

    const result = await api.tour.getSession(storedId, storedToken)
    if (!result.ok) {
      resetTour()
      return false
    }

    if (isAuthenticated.value && result.data.user_id) {
      if (String(result.data.user_id) !== String(user.value?.id)) {
        resetTour()
        return false
      }
    }

    tourSession.value = result.data
    sessionToken.value = storedToken

    if (result.data.status === 'completed') {
      tourStep.value = 'report'
    } else if (result.data.status === 'touring') {
      tourStep.value = 'tour'
      currentHall.value = result.data.current_hall
      if (result.data.current_hall) {
        const exhibitsResult = await api.exhibits.list({ hall: result.data.current_hall })
        if (exhibitsResult.ok) {
          hallExhibits.value = exhibitsResult.data.exhibits || []
        }
      }
    } else if (result.data.status === 'opening') {
      tourStep.value = 'opening'
    } else if (result.data.status === 'onboarding') {
      tourStep.value = 'onboarding'
    }
    return true
  }

  async function fetchHalls() {
    const result = await api.tour.getHalls()
    if (result.ok) {
      halls.value = mergeHallsWithContract(result.data.halls || [])
    }
    return halls.value
  }

  async function selectHall(hallSlug) {
    currentHall.value = hallSlug
    currentExhibit.value = null
    hallExhibits.value = []
    exhibitIndex.value = 0
    streamingContent.value = ''
    suggestedActions.value = null
    chatMessages.value = [{ role: 'assistant', content: buildHallWelcome(hallSlug), isWelcome: true }]
    const token = _getToken()
    await api.tour.updateSession(
      tourSession.value.id,
      {
        current_hall: hallSlug,
        status: 'touring',
      },
      token,
    )
    _persistSession()

    const exhibitsResult = await api.exhibits.list({ hall: hallSlug })
    if (exhibitsResult.ok) {
      hallExhibits.value = exhibitsResult.data.exhibits || []
    }
    bufferEvent('hall_enter', { hall: hallSlug })
  }

  async function enterExhibit(exhibit) {
    if (currentExhibit.value && exhibitStartTime) {
      const duration = Math.floor((Date.now() - exhibitStartTime) / 1000)
      bufferEvent('exhibit_view', {
        exhibit_id: currentExhibit.value.id,
        duration_seconds: duration,
      })
    }
    currentExhibit.value = exhibit
    exhibitStartTime = Date.now()
    chatMessages.value = []
    streamingContent.value = ''
    suggestedActions.value = null

    const token = _getToken()
    await api.tour.updateSession(
      tourSession.value.id,
      {
        current_exhibit_id: exhibit.id,
      },
      token,
    )
  }

  async function sendTourMessage(message, skipUserPush = false, style = null) {
    if (!tourSession.value) return
    const rawMessage = String(message || '').trim()
    if (!rawMessage) return
    loading.value.chat = true
    if (!skipUserPush) {
      chatMessages.value.push({ role: 'user', content: rawMessage })
    }
    bufferEvent('exhibit_question', { message: rawMessage, question: rawMessage })
    streamingContent.value = ''
    suggestedActions.value = null

    const token = _getToken()
    try {
      for await (const event of api.tour.chatStream(
        tourSession.value.id,
        rawMessage,
        token,
        currentExhibit.value?.id,
        style,
        {
          tts: ttsPreferences.value.enabled,
        },
      )) {
        if (event.event === 'chunk' && event.data?.content) {
          streamingContent.value += event.data.content
        } else if (event.event === 'done') {
          const answer = streamingContent.value
          chatMessages.value.push({ role: 'assistant', content: answer })
          bufferEvent('assistant_answer', {
            question: rawMessage,
            answer,
            trace_id: event.data?.trace_id,
          })
          streamingContent.value = ''
          if (event.is_ceramic_question !== undefined || event.suggested_actions) {
            suggestedActions.value = event.suggested_actions || {}
            suggestedActions.value.is_ceramic_question = event.is_ceramic_question || false
          }
        } else if (event.event === 'error') {
          error.value = event.data?.message || 'AI 导览暂时不可用'
        } else if (event.event === 'audio_chunk') {
          if (ttsPreferences.value.enabled && ttsPreferences.value.autoPlay) {
            feedChunk(event.data)
          }
        } else if (event.event === 'audio_error') {
          console.warn('TTS error:', event.data?.message)
        }
      }
    } catch (e) {
      console.error('Tour chat stream error:', e)
      error.value = '连接中断，请重试'
    }
    loading.value.chat = false
  }

  function bufferEvent(eventType, metadata = {}) {
    eventBuffer.push({
      event_type: eventType,
      exhibit_id: currentExhibit.value?.id || metadata.exhibit_id,
      hall: currentHall.value,
      duration_seconds: metadata.duration_seconds,
      metadata,
    })
    _persistEvents()
    if (!eventFlushTimer) {
      eventFlushTimer = setInterval(flushEvents, EVENT_FLUSH_INTERVAL)
    }
  }

  async function flushEvents() {
    if (eventBuffer.length === 0 || !tourSession.value) return
    const events = [...eventBuffer]
    eventBuffer = []
    _persistEvents()

    const token = _getToken()
    const result = await api.tour.recordEvents(tourSession.value.id, events, token)
    if (!result.ok) {
      eventBuffer = [...events, ...eventBuffer]
      _persistEvents()
    }
  }

  async function completeHall() {
    if (!tourSession.value) return
    await flushEvents()

    const token = _getToken()
    const result = await api.tour.completeHall(tourSession.value.id, token)
    if (result.ok) {
      if (result.data.all_halls_visited) {
        tourStep.value = 'report'
      } else {
        tourStep.value = 'hall-select'
        currentHall.value = null
        currentExhibit.value = null
        hallExhibits.value = []
      }
    }
    return result
  }

  async function leaveHall() {
    if (!tourSession.value) return null
    if (currentHall.value) {
      bufferEvent('hall_leave', { hall: currentHall.value })
    }
    await flushEvents()

    const token = _getToken()
    const result = await api.tour.updateSession(
      tourSession.value.id,
      {
        current_hall: null,
        current_exhibit_id: null,
        status: 'touring',
      },
      token,
    )
    if (result.ok) {
      tourSession.value = result.data
    }
    tourStep.value = 'hall-select'
    currentHall.value = null
    currentExhibit.value = null
    hallExhibits.value = []
    exhibitIndex.value = 0
    streamingContent.value = ''
    suggestedActions.value = null
    chatMessages.value = []
    stopTTS()
    return result
  }

  async function generateReport() {
    if (!tourSession.value) return
    loading.value.report = true
    const token = _getToken()
    const result = await api.tour.generateReport(tourSession.value.id, token)
    loading.value.report = false
    if (result.ok) {
      tourReport.value = result.data
    } else {
      error.value = result.data?.detail || '报告生成失败'
    }
    return result
  }

  function resetTour() {
    tourSession.value = null
    sessionToken.value = null
    tourStep.value = 'onboarding'
    currentHall.value = null
    currentExhibit.value = null
    hallExhibits.value = []
    exhibitIndex.value = 0
    streamingContent.value = ''
    suggestedActions.value = null
    chatMessages.value = []
    tourReport.value = null
    error.value = null
    eventBuffer = []
    exhibitStartTime = null
    localStorage.removeItem(STORAGE_KEY_SESSION)
    localStorage.removeItem(STORAGE_KEY_TOKEN)
    localStorage.removeItem(STORAGE_KEY_EVENTS)
    if (eventFlushTimer) {
      clearInterval(eventFlushTimer)
      eventFlushTimer = null
    }
    stopTTS()
  }

  function setupBeforeUnload() {
    window.addEventListener('beforeunload', () => {
      if (eventBuffer.length > 0 && tourSession.value) {
        navigator.sendBeacon(
          `/api/v1/tour/sessions/${tourSession.value.id}/events`,
          JSON.stringify({ events: eventBuffer }),
        )
      }
    })
  }

  const personaLabel = computed(() => BANPO_PERSONA_BY_CODE[tourSession.value?.persona]?.name || '')
  const reportThemeTitle = computed(() => BANPO_PERSONA_BY_CODE[tourSession.value?.persona]?.reportTitle || '')

  return {
    tourSession,
    sessionToken,
    tourStep,
    currentHall,
    currentExhibit,
    hallExhibits,
    exhibitIndex,
    streamingContent,
    suggestedActions,
    chatMessages,
    loading,
    error,
    tourReport,
    halls,
    personaLabel,
    reportThemeTitle,
    ttsPlaying,
    createTourSession,
    restoreSession,
    fetchHalls,
    selectHall,
    enterExhibit,
    sendTourMessage,
    bufferEvent,
    flushEvents,
    completeHall,
    leaveHall,
    generateReport,
    resetTour,
    setupBeforeUnload,
  }
}
