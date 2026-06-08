import { BANPO_EXHIBIT_CATEGORIES } from './banpo.js'

export const EXHIBIT_CATEGORIES = BANPO_EXHIBIT_CATEGORIES

export const CATEGORY_OPTIONS = [
  { value: null, label: '全部' },
  ...EXHIBIT_CATEGORIES,
]

export const FLOOR_OPTIONS = [
  { value: null, label: '全部' },
  { value: 1, label: '一层' },
  { value: 2, label: '二层' },
  { value: 3, label: '三层' },
]

export const CATEGORY_VALUES = EXHIBIT_CATEGORIES.map((category) => category.value)
