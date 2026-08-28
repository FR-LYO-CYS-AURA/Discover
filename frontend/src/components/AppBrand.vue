<template>
  <router-link class="app-brand" :to="{ name: 'Home' }" aria-label="DISCOVER — accueil">
    <img src="@/assets/logo/butterfly.png" alt="DISCOVER" class="app-brand__logo" />
    <span v-if="tag" class="app-brand__tag">{{ tag }}</span>
  </router-link>
</template>

<script setup>
defineProps({
  tag: { type: String, default: '' },
})
</script>

<style scoped>
.app-brand {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  text-decoration: none;
  color: inherit;
}
.app-brand__logo {
  height: 34px;
  width: auto;
  display: block;
}
.app-brand__tag {
  color: var(--text-muted);
  font-size: 13px;
}
</style>
