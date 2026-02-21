<script setup lang="ts">
import { RouterView } from 'vue-router'
import Toast from '@/components/Toast.vue'
import { useToast } from '@/composables/useToast'

const { toasts, removeToast } = useToast()
</script>

<template>
  <RouterView />
  <Toast :toasts="toasts" @close="removeToast" />
</template>

<style>
#app {
  width: 100%;
  min-height: 100vh;
}
</style>
