import { createRouter, createWebHistory } from 'vue-router';
import MainLayout from '@/layouts/MainLayout.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      component: MainLayout,
      children: [
        {
          path: '',
          name: 'home',
          component: () => import('@/views/HomeView.vue'),
        },
        {
          path: 'funds',
          name: 'funds',
          component: () => import('@/views/FundsView.vue'),
        },
        {
          path: 'commodities',
          name: 'commodities',
          component: () => import('@/views/CommoditiesView.vue'),
        },
        {
          path: 'indices',
          name: 'indices',
          component: () => import('@/views/IndicesView.vue'),
        },
        {
          path: 'sectors',
          name: 'sectors',
          component: () => import('@/views/SectorsView.vue'),
        },
        {
          path: 'news',
          name: 'news',
          component: () => import('@/views/NewsView.vue'),
        },
        {
          path: 'bonds',
          name: 'bonds',
          component: () => import('@/views/BondsView.vue'),
        },
        {
          path: 'stocks',
          name: 'stocks',
          component: () => import('@/views/StocksView.vue'),
        },
        {
          path: 'settings',
          name: 'settings',
          component: () => import('@/views/SettingsView.vue'),
        },
      ],
    },
  ],
});

export default router;
