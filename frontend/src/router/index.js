import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import PayView from '../views/PayView.vue'
import ProfileView from '../views/ProfileView.vue'
import AdminView from '../views/AdminView.vue'
import { useAuthStore } from '../stores/auth'

const ADMIN_PATH = import.meta.env.VITE_ADMIN_PATH || '/console'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/pay', name: 'pay', component: PayView, meta: { requiresAuth: true } },
    { path: '/profile', name: 'profile', component: ProfileView, meta: { requiresAuth: true } },
    {
      path: ADMIN_PATH,
      name: 'admin',
      component: AdminView,
      meta: { requiresAuth: true, requiresAdmin: true }
    }
  ]
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    alert('请先登录')
    return { name: 'home' }
  }
  if (to.meta.requiresAdmin) {
    await auth.refreshUser()
    if (!auth.isAdmin) {
      return { name: 'home' }
    }
  }
})

export default router
