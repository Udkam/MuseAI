export const BANPO_HALLS = [
  {
    key: 'basic',
    slug: 'basic-exhibition-hall',
    name: '基本陈列展厅',
    shortName: '陈列',
    icon: '🏺',
    type: '常开放',
    zone: '室内展区',
    floor: 1,
    estimated_duration_minutes: 25,
    display_order: 10,
    description: '以半坡遗址考古发现与研究成果为主线，系统呈现半坡文化的生活形态、生产方式与社会结构。',
    highlights: ['人面鱼纹彩陶盆', '尖底瓶', '彩陶与装饰品', '石器工具'],
  },
  {
    key: 'site',
    slug: 'site-protection-hall',
    name: '遗址保护大厅',
    shortName: '遗址',
    icon: '🏘️',
    type: '常开放',
    zone: '遗址空间',
    floor: 1,
    estimated_duration_minutes: 25,
    display_order: 20,
    description: '强调原址呈现与保护展示，可观察墓葬、地面圆形房屋、烧制作坊、灶具灶台等关键遗存。',
    highlights: ['墓葬', '地面圆形房屋', '烧制作坊', '灶具灶台'],
  },
  {
    key: 'kiln',
    slug: 'kiln-hall',
    name: '陶窑展厅',
    shortName: '陶窑',
    icon: '🔥',
    type: '常开放',
    zone: '工艺展区',
    floor: 1,
    estimated_duration_minutes: 18,
    display_order: 30,
    description: '以“陶器如何被制作出来”为核心叙事，解释制坯、装饰、干燥、入窑烧成等生产流程。',
    highlights: ['陶窑遗迹', '制陶流程', '烧成痕迹', '陶器工艺'],
  },
  {
    key: 'workshop',
    slug: 'prehistoric-workshop',
    name: '史前工坊',
    shortName: '工坊',
    icon: '🛠️',
    type: '常开放',
    zone: '研学体验',
    floor: 2,
    estimated_duration_minutes: 20,
    display_order: 40,
    description: '把制陶、材料、手作等史前生活知识转化为可参与的互动学习体验。',
    highlights: ['手作体验', '史前工艺', '材料认知', '互动学习'],
  },
  {
    key: 'banpoGirl',
    slug: 'banpo-girl-sculpture',
    name: '半坡姑娘雕塑',
    shortName: '雕塑',
    icon: '🗿',
    type: '常开放',
    zone: '公共空间',
    floor: 1,
    estimated_duration_minutes: 8,
    display_order: 50,
    description: '以“半坡姑娘”为代表形象进行艺术化再现，是观众理解半坡人物想象与公共记忆的入口。',
    highlights: ['人物形象', '公共记忆', '艺术再现'],
  },
  {
    key: 'education',
    slug: 'education-center',
    name: '教研中心',
    shortName: '教研',
    icon: '📚',
    type: '常开放',
    zone: '研学空间',
    floor: 2,
    estimated_duration_minutes: 18,
    display_order: 60,
    description: '面向青少年和公众教育活动，适合承载研学课程、主题课堂与研究型活动。',
    highlights: ['教育研学', '主题课堂', '公众活动'],
  },
  {
    key: 'peony',
    slug: 'peony-garden',
    name: '牡丹园',
    shortName: '牡丹园',
    icon: '🌸',
    type: '常开放',
    zone: '园区空间',
    floor: 3,
    estimated_duration_minutes: 10,
    display_order: 70,
    description: '馆区公共景观空间，可作为路线间的缓冲和观众休整点。',
    highlights: ['园区景观', '休整空间', '公共体验'],
  },
  {
    key: 'temp1',
    slug: 'temporary-hall-1',
    name: '临展厅一',
    shortName: '临展一',
    icon: '🖼️',
    type: '临展',
    zone: '临时展览',
    floor: 3,
    estimated_duration_minutes: 15,
    display_order: 90,
    description: '临时展览空间，当前主题需按馆方最新展陈内容更新。',
    highlights: ['临时展览', '主题待定'],
  },
  {
    key: 'temp2',
    slug: 'temporary-hall-2',
    name: '临展厅二',
    shortName: '临展二',
    icon: '🖼️',
    type: '临展',
    zone: '临时展览',
    floor: 3,
    estimated_duration_minutes: 15,
    display_order: 100,
    description: '临时展览空间，当前主题需按馆方最新展陈内容更新。',
    highlights: ['临时展览', '主题待定'],
  },
]

export const BANPO_HALLS_BY_SLUG = Object.fromEntries(BANPO_HALLS.map((hall) => [hall.slug, hall]))
export const BANPO_HALLS_BY_KEY = Object.fromEntries(BANPO_HALLS.map((hall) => [hall.key, hall]))
export const CANONICAL_HALL_SLUGS = new Set(BANPO_HALLS.map((hall) => hall.slug))

export function normalizeHallSlug(value) {
  if (!value) return ''
  return CANONICAL_HALL_SLUGS.has(value) ? value : ''
}

export function isCanonicalHallSlug(value) {
  return CANONICAL_HALL_SLUGS.has(value)
}

export function getHallBySlug(value) {
  return BANPO_HALLS_BY_SLUG[normalizeHallSlug(value)] || null
}

export function getHallDisplayName(value) {
  return getHallBySlug(value)?.name || value || '未选择展厅'
}

export function createHallPayload(hall) {
  return {
    slug: hall.slug,
    name: hall.name,
    description: hall.description,
    floor: hall.floor,
    estimated_duration_minutes: hall.estimated_duration_minutes,
    display_order: hall.display_order,
    is_active: true,
  }
}

export function normalizeHallRecord(record) {
  if (!record) return null
  const rawSlug = record.slug || record.hall || record.hall_slug
  const slug = normalizeHallSlug(rawSlug)
  const contract = BANPO_HALLS_BY_SLUG[slug]
  return {
    ...record,
    slug,
    contract,
    isLegacy: Boolean(rawSlug && rawSlug !== slug),
  }
}

export function mergeHallsWithContract(records = []) {
  const bySlug = new Map()
  for (const item of records) {
    const normalized = normalizeHallRecord(item)
    if (normalized?.slug && !bySlug.has(normalized.slug)) {
      bySlug.set(normalized.slug, normalized)
    }
  }

  return BANPO_HALLS.map((hall) => {
    const backend = bySlug.get(hall.slug)
    return {
      ...hall,
      ...backend,
      slug: hall.slug,
      name: hall.name,
      shortName: hall.shortName,
      icon: hall.icon,
      type: hall.type,
      zone: hall.zone,
      description: hall.description,
      highlights: hall.highlights,
      floor: hall.floor,
      estimated_duration_minutes: backend?.estimated_duration_minutes ?? hall.estimated_duration_minutes,
      display_order: hall.display_order,
      is_active: backend?.is_active ?? true,
      exhibit_count: backend?.exhibit_count ?? 0,
      hasBackend: Boolean(backend),
      contract: hall,
    }
  }).sort((a, b) => a.display_order - b.display_order)
}

export function getLegacyHallRows(records = []) {
  return records
    .filter((item) => {
      const rawSlug = item?.slug || item?.hall || item?.hall_slug
      return rawSlug && !CANONICAL_HALL_SLUGS.has(rawSlug)
    })
    .map((item) => {
      const rawSlug = item.slug || item.hall || item.hall_slug
      return {
        ...item,
        targetSlug: '',
        targetName: '契约外展厅',
      }
    })
}

export const BANPO_PERSONAS = [
  {
    code: 'A',
    personaId: 'A',
    focusId: 'research',
    name: '考古研究员',
    focusTitle: '证据怎样成史',
    routeTitle: '考古研究路线',
    reportTitle: '半坡考古研究报告',
    color: 'warning',
    prompt: '像研究者一样，看证据、推理和不确定性。',
  },
  {
    code: 'B',
    personaId: 'B',
    focusId: 'study',
    name: '研学记录员',
    focusTitle: '带着任务研学',
    routeTitle: '研学记录路线',
    reportTitle: '半坡研学记录报告',
    color: 'success',
    prompt: '边看边记，把展厅整理成可复盘的笔记。',
  },
  {
    code: 'C',
    personaId: 'C',
    focusId: 'history',
    name: '历史追问者',
    focusTitle: '历史问题追问',
    routeTitle: '历史追问路线',
    reportTitle: '半坡历史追问报告',
    color: 'primary',
    prompt: '把半坡放进更大的史前中国和今天来理解。',
  },
  {
    code: 'D',
    personaId: 'D',
    focusId: 'object-study',
    name: '器物研究员',
    focusTitle: '器物细节观察',
    routeTitle: '器物观察路线',
    reportTitle: '半坡器物观察报告',
    color: 'info',
    prompt: '从材料、器形、纹饰和工艺读懂文物。',
  },
]

export const BANPO_PERSONA_BY_CODE = Object.fromEntries(BANPO_PERSONAS.map((item) => [item.code, item]))

export const BANPO_ASSUMPTIONS = [
  { code: 'A', label: '更像平等互助的共同体' },
  { code: 'B', label: '艰难但有烟火气的生活' },
  { code: 'C', label: '已经出现分工和规则' },
  { code: 'D', label: '先不下判断，跟证据走' },
]

export const BANPO_RHYTHMS = [
  { value: 'notebook', label: '研学记录模式' },
  { value: 'quick', label: '30 分钟抓重点' },
  { value: 'dialogue', label: '1 小时边看边问' },
  { value: 'research', label: '研究深化模式' },
]

function routeStep(slug, title, focus, minutes) {
  const hall = getHallBySlug(slug)
  return {
    hall_slug: slug,
    hall_name: hall?.name || slug,
    title,
    focus,
    estimated_minutes: minutes,
    tags: hall?.highlights?.slice(0, 3) || [],
  }
}

export const BANPO_ROUTE_STRATEGIES = {
  A: {
    persona: BANPO_PERSONA_BY_CODE.A,
    summary: '先建立文物证据框架，再回到遗址空间和陶器工艺中验证推断。',
    total_minutes: 90,
    steps: [
      routeStep('basic-exhibition-hall', '建立证据框架', '看器物、出土背景和展签如何支撑判断。', 20),
      routeStep('site-protection-hall', '回到原址验证', '把房屋、墓葬和壕沟放回真实聚落空间中理解。', 20),
      routeStep('kiln-hall', '追踪制陶证据', '从烧成痕迹和工艺流程检验“陶器如何生产”。', 15),
      routeStep('prehistoric-workshop', '补足实验体验', '用操作难度理解工具和工艺背后的劳动经验。', 15),
      routeStep('banpo-girl-sculpture', '辨析想象与证据', '区分考古事实、艺术再现和公共记忆。', 10),
      routeStep('education-center', '整理研究问题', '把观察点整理成证据链和待查问题。', 10),
    ],
  },
  B: {
    persona: BANPO_PERSONA_BY_CODE.B,
    summary: '按“领任务、记证据、成笔记”的节奏，把参观材料整理成可复盘的研学记录。',
    total_minutes: 90,
    steps: [
      routeStep('site-protection-hall', '先领观察任务', '记录房屋、墓葬、公共空间的相互位置。', 18),
      routeStep('basic-exhibition-hall', '补充展品证据', '记录器物名称、用途、材料和能说明问题的细节。', 22),
      routeStep('education-center', '整理问题清单', '把观察整理成问题链、证据链和小结。', 15),
      routeStep('prehistoric-workshop', '动手理解工艺', '记录手作环节、难点和展品之间的对应关系。', 15),
      routeStep('kiln-hall', '理解陶器生产', '把制陶流程补进研学笔记。', 12),
      routeStep('banpo-girl-sculpture', '形成复盘入口', '记录人物形象如何影响今天对半坡的第一印象。', 8),
    ],
  },
  C: {
    persona: BANPO_PERSONA_BY_CODE.C,
    summary: '从日常生活的问题进入，再追问聚落组织、公共记忆和今天如何理解半坡。',
    total_minutes: 90,
    steps: [
      routeStep('basic-exhibition-hall', '从生活问题开始', '看吃住劳动、器物用途和装饰如何组织日常。', 20),
      routeStep('site-protection-hall', '追问聚落关系', '观察房屋、墓葬和公共空间是否体现规则。', 20),
      routeStep('banpo-girl-sculpture', '看公共记忆', '思考现代雕塑如何塑造半坡人的形象。', 10),
      routeStep('peony-garden', '换到公共空间', '把博物馆园区也作为今天的展示和休整空间来理解。', 10),
      routeStep('education-center', '整理追问线索', '把“为什么”和“还有什么证据”整理成后续问题。', 15),
      routeStep('kiln-hall', '回到工艺证据', '用陶窑生产补充对社会分工的讨论。', 15),
    ],
  },
  D: {
    persona: BANPO_PERSONA_BY_CODE.D,
    summary: '从代表性器物进入，再回到遗址和工艺流程，用细节建立可解释的半坡图景。',
    total_minutes: 90,
    steps: [
      routeStep('basic-exhibition-hall', '先看器物成品', '观察材料、器形、纹饰和磨损痕迹。', 23),
      routeStep('kiln-hall', '再理解制作过程', '从陶窑、烧成痕迹和制陶流程理解工艺链条。', 17),
      routeStep('prehistoric-workshop', '用体验验证难度', '把“好看”“有用”“难做”拆成可观察证据。', 15),
      routeStep('site-protection-hall', '放回使用场景', '看器物如何进入房屋、墓葬和公共空间。', 20),
      routeStep('banpo-girl-sculpture', '区分器物与形象', '辨析实物证据和艺术想象的边界。', 8),
      routeStep('education-center', '整理器物卡片', '形成可复盘的器物观察表。', 7),
    ],
  },
}

export const TTS_VOICE_CONTRACT = {
  voice: '冰糖',
  label: '冰糖（美少女声线）',
  description: '清甜明亮，语速自然偏快，停顿短，适合博物馆公共空间的轻声讲解。',
  sample: '这里是半坡遗址。先看眼前这件器物，再判断它能说明什么。',
}

export const BANPO_EXHIBIT_CATEGORIES = [
  { value: 'painted_pottery', label: '彩陶与纹饰' },
  { value: 'pottery', label: '陶器' },
  { value: 'stone_tool', label: '石器工具' },
  { value: 'bone_tool', label: '骨器' },
  { value: 'settlement', label: '聚落遗址' },
  { value: 'burial', label: '墓葬与体质人类学' },
  { value: 'production', label: '生产与工艺' },
  { value: 'symbol', label: '符号与精神文化' },
  { value: 'education', label: '研学体验' },
  { value: 'temporary', label: '临展内容' },
]

export function getCategoryLabel(value) {
  return BANPO_EXHIBIT_CATEGORIES.find((item) => item.value === value)?.label || value || '未分类'
}
