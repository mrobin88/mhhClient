import { createRouter, createWebHashHistory } from 'vue-router'
import StaffLogin from './components/StaffLogin.vue'
import StaffForgotPassword from './components/StaffForgotPassword.vue'
import StaffResetPassword from './components/StaffResetPassword.vue'
import StaffDashboard from './components/StaffDashboard.vue'
import StaffClientList from './components/StaffClientList.vue'
import StaffClientCreate from './components/StaffClientCreate.vue'
import StaffClientDetail from './components/StaffClientDetail.vue'
import StaffMessages from './components/StaffMessages.vue'
import StaffCreateSkill from './components/StaffCreateSkill.vue'
import StaffClasses from './components/StaffClasses.vue'
import StaffTickets from './components/StaffTickets.vue'
import StaffTicketDetail from './components/StaffTicketDetail.vue'
import StaffHowItWorks from './components/StaffHowItWorks.vue'

export function createStaffRouter() {
  return createRouter({
    history: createWebHashHistory(),
    routes: [
      { path: '/', redirect: '/dashboard' },
      { path: '/login', name: 'Login', component: StaffLogin, meta: { guest: true } },
      { path: '/forgot-password', name: 'ForgotPassword', component: StaffForgotPassword, meta: { guest: true } },
      {
        path: '/reset-password/:uid/:token',
        name: 'ResetPassword',
        component: StaffResetPassword,
        meta: { guest: true },
      },
      { path: '/dashboard', name: 'Dashboard', component: StaffDashboard },
      { path: '/clients', name: 'Clients', component: StaffClientList },
      { path: '/clients/new', name: 'ClientCreate', component: StaffClientCreate },
      { path: '/clients/:id', name: 'ClientDetail', component: StaffClientDetail },
      { path: '/messages', name: 'Messages', component: StaffMessages },
      { path: '/classes', name: 'Classes', component: StaffClasses },
      { path: '/tickets', name: 'Tickets', component: StaffTickets },
      { path: '/tickets/:id', name: 'TicketDetail', component: StaffTicketDetail },
      { path: '/create-skill', name: 'CreateSkill', component: StaffCreateSkill },
      { path: '/how-it-works', name: 'HowItWorks', component: StaffHowItWorks },
    ],
  })
}
