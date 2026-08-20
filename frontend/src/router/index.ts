import { createRouter, createWebHistory } from 'vue-router'
import ClientForm from '../components/ClientForm.vue'
import CheckInApp from '../checkin/CheckInApp.vue'
import DocumentUploadInvite from '../components/DocumentUploadInvite.vue'

export default createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'intake', component: ClientForm },
    { path: '/checkin', name: 'checkin', component: CheckInApp },
    { path: '/upload/:token', name: 'document-upload', component: DocumentUploadInvite },
  ],
})
