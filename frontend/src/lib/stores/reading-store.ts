export type ReadingPreferences = {
  fontSize: number
  lineSpacing: number
  contentWidth: number
  theme: 'light' | 'dark'
}

export type ReadingState = {
  open: boolean
  mode: 'pdf' | 'text' | 'home'
  currentPage: number
  currentDocId: string | null
  preferences: ReadingPreferences
}

export const defaultPreferences: ReadingPreferences = {
  fontSize: 16,
  lineSpacing: 1.5,
  contentWidth: 800,
  theme: 'light',
}

export const defaultReadingState: ReadingState = {
  open: false,
  mode: 'home',
  currentPage: 1,
  currentDocId: null,
  preferences: { ...defaultPreferences },
}