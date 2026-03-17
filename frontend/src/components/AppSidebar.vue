<template>
  <aside
    class="sidebar"
    :class="{ 'sidebar--collapsed': isCollapsed }"
    role="navigation"
    :aria-label="$t('app.name')"
  >
    <!-- Logo / brand -->
    <div class="sidebar__brand">
      <RouterLink to="/" class="sidebar__logo" :aria-label="$t('app.name')">
        <span class="sidebar__logo-mark">T</span>
        <Transition name="fade">
          <span v-if="!isCollapsed" class="sidebar__logo-name"
            >aste<em>Base</em></span
          >
        </Transition>
      </RouterLink>
    </div>

    <div class="sidebar__divider" />

    <!-- Domain navigation -->
    <nav class="sidebar__nav">
      <!-- Home -->
      <RouterLink
        to="/"
        class="sidebar__link"
        :class="{ 'sidebar__link--active': $route.path === '/' }"
        :title="isCollapsed ? $t('nav.home') : undefined"
      >
        <span class="sidebar__link-icon sidebar__link-icon--home">⌂</span>
        <Transition name="fade">
          <span v-if="!isCollapsed" class="sidebar__link-label">{{
            $t("nav.home")
          }}</span>
        </Transition>
      </RouterLink>

      <div class="sidebar__divider sidebar__divider--subtle" />

      <!-- Domain links -->
      <RouterLink
        v-for="domain in DOMAINS"
        :key="domain.key"
        :to="domain.route"
        class="sidebar__link"
        :class="{
          'sidebar__link--active': $route.path === domain.route,
        }"
        :style="{ '--domain-color': domain.color }"
        :title="isCollapsed ? $t(domain.labelKey) : undefined"
      >
        <span class="sidebar__link-icon">{{ domain.icon }}</span>
        <Transition name="fade">
          <span v-if="!isCollapsed" class="sidebar__link-label">{{
            $t(domain.labelKey)
          }}</span>
        </Transition>
      </RouterLink>
    </nav>

    <!-- Bottom: language toggle + collapse -->
    <div class="sidebar__footer">
      <!-- Language toggle -->
      <button
        class="sidebar__link sidebar__link--action"
        :title="isCollapsed ? currentLocaleLabel : undefined"
        @click="toggleLocale"
      >
        <span class="sidebar__link-icon">◎</span>
        <Transition name="fade">
          <span v-if="!isCollapsed" class="sidebar__link-label">{{
            currentLocaleLabel
          }}</span>
        </Transition>
      </button>

      <!-- Collapse toggle (desktop only) -->
      <button
        class="sidebar__collapse-btn"
        :aria-label="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'"
        @click="isCollapsed = !isCollapsed"
      >
        <span
          :class="
            isCollapsed
              ? 'sidebar__collapse-icon--open'
              : 'sidebar__collapse-icon--close'
          "
        >
          {{ isCollapsed ? "›" : "‹" }}
        </span>
      </button>
    </div>
  </aside>
</template>

<script setup>
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { DOMAINS } from "@/config/domains";

const { locale, t } = useI18n();

// Sidebar collapsed state (persisted in localStorage)
const isCollapsed = ref(
  localStorage.getItem("tastebase-sidebar-collapsed") === "true",
);

// Watch for changes and persist
import { watch } from "vue";
watch(isCollapsed, (val) => {
  localStorage.setItem("tastebase-sidebar-collapsed", String(val));
  // Sync CSS custom property on root for main content margin
  document.documentElement.style.setProperty(
    "--sidebar-current-width",
    val ? "64px" : "220px",
  );
});

// Language toggle
const currentLocaleLabel = computed(() =>
  locale.value === "fr" ? "FR" : "EN",
);

function toggleLocale() {
  const next = locale.value === "fr" ? "en" : "fr";
  locale.value = next;
  localStorage.setItem("tastebase-locale", next);
  document.documentElement.lang = next;
}
</script>

<style lang="scss" scoped>
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: $sidebar-width;
  background-color: $color-bg-elevated;
  border-right: 1px solid $color-border-subtle;
  display: flex;
  flex-direction: column;
  z-index: 100;
  transition: width $transition-normal;
  overflow: hidden;

  // Collapsed state
  &--collapsed {
    width: $sidebar-width-mini;

    // Sync main content offset via CSS variable
    ~ .app-main {
      margin-left: $sidebar-width-mini;
    }
  }
}

// Brand / logo
.sidebar__brand {
  padding: $space-6 $space-4;
  flex-shrink: 0;
}

.sidebar__logo {
  display: flex;
  align-items: center;
  gap: $space-2;
  color: $color-text-primary;
  text-decoration: none;

  &:hover .sidebar__logo-mark {
    color: $color-accent;
  }
}

.sidebar__logo-mark {
  font-family: $font-display;
  font-size: $text-2xl;
  font-weight: $font-weight-semi;
  color: $color-accent;
  line-height: 1;
  width: 32px;
  text-align: center;
  flex-shrink: 0;
  transition: color $transition-fast;
}

.sidebar__logo-name {
  font-family: $font-display;
  font-size: $text-lg;
  font-weight: $font-weight-light;
  color: $color-text-primary;
  white-space: nowrap;

  em {
    font-style: italic;
    color: $color-text-secondary;
  }
}

// Navigation
.sidebar__nav {
  flex: 1;
  padding: $space-2 $space-3;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar__link {
  display: flex;
  align-items: center;
  gap: $space-3;
  padding: $space-2 $space-3;
  border-radius: $radius-md;
  color: $color-text-secondary;
  font-size: $text-sm;
  font-weight: $font-weight-regular;
  transition:
    color $transition-fast,
    background-color $transition-fast;
  cursor: pointer;
  white-space: nowrap;
  width: 100%;
  text-align: left;
  margin-bottom: $space-1;

  &:hover {
    color: $color-text-primary;
    background-color: rgba(255, 255, 255, 0.04);
  }

  // Active state — uses domain color via CSS custom property
  &--active {
    color: var(--domain-color, $color-accent);
    background-color: rgba(var(--domain-color, #c9a96e), 0.08);

    .sidebar__link-icon {
      color: var(--domain-color, $color-accent);
    }
  }

  &--action {
    background: none;
    border: none;
    font-family: inherit;
  }
}

// Home link has gold accent (no domain color)
.sidebar__link:first-child {
  --domain-color: #{$color-accent};
}

.sidebar__link-icon {
  font-size: $text-base;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
  color: $color-text-muted;
  transition: color $transition-fast;
}

.sidebar__link-icon--home {
  font-size: $text-lg;
}

.sidebar__link-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

// Dividers
.sidebar__divider {
  height: 1px;
  background-color: $color-border-subtle;
  margin: $space-3 $space-4;
  flex-shrink: 0;

  &--subtle {
    background-color: transparent;
    margin: $space-1 $space-4;
  }
}

// Footer
.sidebar__footer {
  padding: $space-3;
  flex-shrink: 0;
  border-top: 1px solid $color-border-subtle;
  display: flex;
  flex-direction: column;
  gap: $space-1;
}

.sidebar__collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: $space-2;
  border-radius: $radius-md;
  color: $color-text-muted;
  font-size: $text-lg;
  transition:
    color $transition-fast,
    background-color $transition-fast;

  &:hover {
    color: $color-text-primary;
    background-color: rgba(255, 255, 255, 0.04);
  }

  @media (max-width: #{$bp-md - 1px}) {
    display: none;
  }
}

// Fade transition for labels
.fade-enter-active,
.fade-leave-active {
  transition: opacity $transition-fast;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
