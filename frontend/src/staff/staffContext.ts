import type { InjectionKey, Ref } from 'vue'
import type { StaffUser } from './types'

export type StaffPrefsPatch = {
  accent_color?: string
  dashboard_collapsed?: string[]
}

export const staffUserKey: InjectionKey<Ref<StaffUser | null>> = Symbol('staffUser')
export const setStaffUserKey: InjectionKey<(user: StaffUser | null) => void> = Symbol('setStaffUser')
export const saveStaffPrefsKey: InjectionKey<
  (patch: StaffPrefsPatch, options?: { persist?: boolean }) => Promise<boolean>
> = Symbol('saveStaffPrefs')
