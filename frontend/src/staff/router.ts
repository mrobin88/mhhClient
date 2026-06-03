import { createRouter, createWebHashHistory } from 'vue-router'
import StaffLogin from './components/StaffLogin.vue'
import StaffForgotPassword from './components/StaffForgotPassword.vue'
import StaffResetPassword from './components/StaffResetPassword.vue'
import StaffClientList from './components/StaffClientList.vue'
import StaffClientDetail from './components/StaffClientDetail.vue'
import StaffMessages from './components/StaffMessages.vue'
import StaffCreateSkill from './components/StaffCreateSkill.vue'

export function createStaffRouter() {
  return createRouter({
    history: createWebHashHistory(),
    routes: [
      { path: '/', redirect: '/clients' },
      { path: '/login', name: 'Login', component: StaffLogin, meta: { guest: true } },
      { path: '/forgot-password', name: 'ForgotPassword', component: StaffForgotPassword, meta: { guest: true } },
      {
        path: '/reset-password/:uid/:token',
        name: 'ResetPassword',
        component: StaffResetPassword,
        meta: { guest: true },
      },
      { path: '/clients', name: 'Clients', component: StaffClientList },
      { path: '/clients/:id', name: 'ClientDetail', component: StaffClientDetail },
      { path: '/messages', name: 'Messages', component: StaffMessages },
      { path: '/create-skill', name: 'CreateSkill', component: StaffCreateSkill },
    ],
  })
}
