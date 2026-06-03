import { createApp } from 'vue'
import '../style.css'
import './staff.css'
import StaffApp from './StaffApp.vue'
import { createStaffRouter } from './router'

const app = createApp(StaffApp)
const router = createStaffRouter()
app.use(router)
app.mount('#app')
