<script setup>
import { ref, onMounted } from 'vue'
import { useTour } from '../../composables/useTour.js'

const props = defineProps({ hall: String, hallName: String })
const emit = defineEmits(['done'])

const { tourSession, sendTourMessage, streamingContent, chatMessages, loading } = useTour()

const hallIntroPrompts = {
  A: `请以考古研究员的身份介绍${props.hallName}。说明这个展厅适合观察哪些证据、哪些判断需要谨慎，3句话以内。`,
  B: `请以研学记录员的身份介绍${props.hallName}。给出本展厅的观察任务、记录重点和可复盘问题，3句话以内。`,
  C: `请以历史追问者的身份介绍${props.hallName}。说明这个展厅能引出哪些关于史前社会的问题，3句话以内。`,
  D: `请以器物研究员的身份介绍${props.hallName}。提示用户关注材料、器形、纹饰、制作痕迹和使用场景，3句话以内。`,
}

onMounted(async () => {
  await sendTourMessage(hallIntroPrompts[tourSession.value?.persona || 'A'])
})

function continueTour() { emit('done') }
</script>

<template>
  <div class="hall-intro">
    <h2 class="hall-title">{{ hallName }}</h2>
    <div class="intro-content">
      <template v-if="chatMessages.length > 0">
        <p v-for="msg in chatMessages.filter(m => m.role === 'assistant')" :key="msg.content" class="intro-text">{{ msg.content }}</p>
      </template>
      <p v-if="loading.chat" class="intro-text typing">{{ streamingContent }}<span class="cursor">|</span></p>
    </div>
    <el-button v-if="!loading.chat && chatMessages.length > 0" type="primary" @click="continueTour">开始参观 →</el-button>
  </div>
</template>

<style scoped>
.hall-intro { padding: 40px 24px; text-align: center; max-width: 640px; margin: 0 auto; }
.hall-title { font-size: 24px; color: var(--color-accent); margin-bottom: 24px; }
.intro-content { margin-bottom: 32px; }
.intro-text { font-size: 16px; line-height: 2; color: var(--color-text-primary); text-align: left; white-space: pre-wrap; }
.cursor { animation: blink 0.8s infinite; color: var(--color-accent); }
@keyframes blink { 0%,50%{opacity:1} 51%,100%{opacity:0} }
</style>
