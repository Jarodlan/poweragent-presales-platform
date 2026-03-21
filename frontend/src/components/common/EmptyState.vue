<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>

<template>
  <div class="empty-state">
    <div class="empty-state__badge">PowerAgent</div>
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty-state {
  max-width: 680px;
  margin: 64px auto;
  padding: 48px 36px;
  text-align: center;
  border: 1px dashed rgba(15, 93, 140, 0.22);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.78);
}

.empty-state__badge {
  display: inline-flex;
  padding: 6px 12px;
  border-radius: 999px;
  margin-bottom: 18px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

h2 {
  margin: 0 0 10px;
  font-size: 30px;
}

p {
  margin: 0;
  line-height: 1.75;
  color: var(--muted);
}
</style>
