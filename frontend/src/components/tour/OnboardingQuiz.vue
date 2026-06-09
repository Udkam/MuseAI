<script setup>
import { ref } from 'vue'
import { useTour } from '../../composables/useTour.js'

const { createTourSession, tourStep } = useTour()

const currentQuestion = ref(0)
const answers = ref({ interest_type: null, persona: null, assumption: null })
const loading = ref(false)

const questions = [
  {
    key: 'interest_type',
    title: '今天你最希望从哪个角度进入半坡？',
    options: [
      { value: 'A', label: '带着任务研学', desc: '边看边记，把展厅整理成可复盘的笔记' },
      { value: 'B', label: '证据怎样成史', desc: '像研究者一样，看证据、推理和不确定性' },
      { value: 'C', label: '历史问题追问', desc: '把半坡放进更大的史前中国和今天来理解' },
      { value: 'D', label: '器物细节观察', desc: '从材料、器形、纹饰和工艺读懂文物' },
    ],
  },
  {
    key: 'persona',
    title: '接下来希望 MuseAI 以哪种身份陪你？',
    options: [
      { value: 'A', label: '考古研究员', desc: '从地层、遗存和证据链进入问题' },
      { value: 'B', label: '研学记录员', desc: '把观察转化为任务、记录点和摘要' },
      { value: 'C', label: '历史追问者', desc: '持续追问制度、公共生活和历史解释' },
      { value: 'D', label: '器物研究员', desc: '聚焦器形、纹饰、工艺和使用场景' },
    ],
  },
  {
    key: 'assumption',
    title: '凭直觉，你认为半坡文明最重要的线索是？',
    options: [
      { value: 'A', label: '工艺', desc: '陶器、石器和骨器如何被制作出来' },
      { value: 'B', label: '聚落', desc: '房屋、壕沟、墓葬如何组织空间' },
      { value: 'C', label: '社会组织', desc: '分工、协作、规则和公共生活如何形成' },
      { value: 'D', label: '精神文化', desc: '图案、仪式和形象如何表达观念' },
    ],
  },
]

async function selectOption(value) {
  const q = questions[currentQuestion.value]
  answers.value[q.key] = value

  if (currentQuestion.value < questions.length - 1) {
    currentQuestion.value++
  } else {
    loading.value = true
    const session = await createTourSession(
      answers.value.interest_type,
      answers.value.persona,
      answers.value.assumption,
    )
    loading.value = false
    if (session) {
      tourStep.value = 'opening'
    }
  }
}
</script>

<template>
  <div class="onboarding">
    <div class="onboarding-inner">
      <div class="progress">
        <span v-for="i in 3" :key="i" class="dot" :class="{ active: i <= currentQuestion + 1, done: i < currentQuestion + 1 }" />
      </div>

      <transition name="fade" mode="out-in">
        <div :key="currentQuestion" class="question-card">
          <h2 class="question-title">{{ questions[currentQuestion].title }}</h2>
          <div class="options">
            <div
              v-for="opt in questions[currentQuestion].options"
              :key="opt.value"
              class="option-card"
              @click="selectOption(opt.value)"
            >
              <span class="option-letter">{{ opt.value }}</span>
              <div class="option-content">
                <span class="option-label">{{ opt.label }}</span>
                <span v-if="opt.desc" class="option-desc">{{ opt.desc }}</span>
              </div>
            </div>
          </div>
        </div>
      </transition>

      <div v-if="loading" class="loading-overlay">
        <el-icon class="is-loading" :size="32"><Loading /></el-icon>
        <span>正在为你准备专属导览...</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.onboarding {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100%;
  padding: 40px 20px;
}

.onboarding-inner {
  max-width: 640px;
  width: 100%;
}

.progress {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 40px;
}

.dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-bg-subtle);
  transition: all 0.3s;
}

.dot.active {
  background: var(--color-accent);
}

.dot.done {
  background: #8fbc8f;
}

.question-card {
  text-align: center;
}

.question-title {
  font-size: 22px;
  line-height: 1.6;
  margin-bottom: 32px;
  color: var(--color-text-primary);
}

.options {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.option-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.option-card:hover {
  background: var(--color-accent-muted);
  border-color: var(--color-accent);
  transform: translateX(4px);
}

.option-letter {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: var(--color-accent-muted);
  color: var(--color-accent);
  font-weight: 700;
  font-size: 16px;
  flex-shrink: 0;
}

.option-content {
  display: flex;
  flex-direction: column;
  text-align: left;
}

.option-label {
  font-size: 16px;
  line-height: 1.5;
}

.option-desc {
  font-size: 13px;
  color: var(--color-text-muted);
  margin-top: 4px;
}

.loading-overlay {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  background: var(--color-bg-base);
  z-index: 100;
  color: var(--color-accent);
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}
</style>
