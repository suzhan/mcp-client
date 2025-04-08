import { createRouter, createWebHistory } from 'vue-router';
import Home from '../views/Home.vue';
import Chat from '../views/Chat.vue';
import Servers from '../views/Servers.vue';
import Providers from '../views/Providers.vue';
import Settings from '../views/Settings.vue';

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Home
    },
    {
      path: '/chat/new',
      name: 'new-chat',
      component: Chat
    },
    {
      path: '/chat/:id',
      name: 'chat',
      component: Chat,
      props: true
    },
    {
      path: '/servers',
      name: 'servers',
      component: Servers
    },
    {
      path: '/providers',
      name: 'providers',
      component: Providers
    },
    {
      path: '/settings',
      name: 'settings',
      component: Settings
    }
  ]
});

export default router; 