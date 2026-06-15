import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import PayView from '../views/PayView.vue'
import AdminView from '../views/AdminView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/pay', name: 'pay', component: PayView, meta: { requiresAuth: true } },
    {
      path: '/admin',
      name: 'admin',
      component: AdminView,
      meta: { requiresAuth: true, requiresAdmin: true }
    }
  ]
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    alert('请先登录')
    return { name: 'home' }
  }
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    alert('请以管理员身份登录')
    return { name: 'home' }
  }
})

export default router
