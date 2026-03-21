import { defineStore } from 'pinia'
import { ref } from 'vue'

import { fetchMetaOptions } from '@/api/meta'
import type { MetaOptions } from '@/types/meta'

export const useMetaStore = defineStore('meta', () => {
  const options = ref<MetaOptions | null>(null)
  const loading = ref(false)

  async function loadOptions() {
    if (options.value || loading.value) return
    loading.value = true
    try {
      options.value = await fetchMetaOptions()
    } finally {
      loading.value = false
    }
  }

  return {
    options,
    loading,
    loadOptions,
  }
})
