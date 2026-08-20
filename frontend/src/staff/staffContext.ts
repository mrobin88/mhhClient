import type { InjectionKey, Ref } from 'vue'
import type { StaffUser } from './types'

export const staffUserKey: InjectionKey<Ref<StaffUser | null>> = Symbol('staffUser')
export const setStaffUserKey: InjectionKey<(user: StaffUser | null) => void> = Symbol('setStaffUser')
