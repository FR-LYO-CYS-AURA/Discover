<template>
  <transition name="loading-fade">
    <div
      v-if="shown"
      :class="['loading-screen', { 'loading-screen--fullscreen': fullscreen }]"
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div class="loading-screen__stage">
        <span class="loading-screen__ring" aria-hidden="true"></span>
        <img
          src="@/assets/logo/butterfly@256.png"
          alt=""
          class="loading-screen__logo"
          aria-hidden="true"
        />
      </div>
      <p v-if="label" class="loading-screen__label">{{ label }}</p>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  // Contrôle l'affichage demandé par la vue parente.
  visible: { type: Boolean, default: false },
  // Libellé discret sous le logo (ex. étape en cours). Vide = aucun texte.
  label: { type: String, default: '' },
  // Délai anti-flash : l'écran n'apparaît qu'au-delà de ce seuil (ms).
  delay: { type: Number, default: 300 },
  // true = couvre toute la fenêtre ; false = couvre le conteneur parent (position: relative requise).
  fullscreen: { type: Boolean, default: false },
})

// `shown` est l'état réellement rendu ; il ne suit `visible` qu'après le délai.
const shown = ref(false)
let timer = null

function clearTimer() {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
}

watch(
  () => props.visible,
  (v) => {
    clearTimer()
    if (v) {
      if (props.delay > 0) {
        timer = setTimeout(() => {
          shown.value = true
          timer = null
        }, props.delay)
      } else {
        shown.value = true
      }
    } else {
      // Attente terminée : on masque immédiatement (et on annule un affichage en attente).
      shown.value = false
    }
  },
  { immediate: true },
)

onBeforeUnmount(clearTimer)
</script>

<style scoped>
.loading-screen {
  position: absolute;
  inset: 0;
  z-index: var(--z-overlay, 100);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 22px;
  background: var(--overlay-strong, rgba(251, 251, 251, 0.94));
  backdrop-filter: blur(2px);
}
.loading-screen--fullscreen {
  position: fixed;
}

.loading-screen__stage {
  position: relative;
  width: 132px;
  height: 132px;
  display: grid;
  place-items: center;
}
.loading-screen__ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 3px solid var(--border, #e6e6e6);
  border-top-color: var(--accent, #00b8d4);
  animation: spin 0.9s linear infinite;
}
.loading-screen__logo {
  width: 72px;
  height: auto;
  display: block;
  user-select: none;
  -webkit-user-drag: none;
}
.loading-screen__label {
  margin: 0;
  color: var(--text-muted, #6a6a6a);
  font-size: 14px;
  letter-spacing: 0.2px;
  text-align: center;
}

.loading-fade-enter-active,
.loading-fade-leave-active {
  transition: opacity 0.2s ease;
}
.loading-fade-enter-from,
.loading-fade-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .loading-screen__ring {
    animation-duration: 2.4s;
  }
}

@media print {
  .loading-screen {
    display: none !important;
  }
}
</style>
