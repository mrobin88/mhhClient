<script setup lang="ts">
import ClientForm from './components/ClientForm.vue'
</script>

<template>
  <ClientForm />
</template>

<style>
/* Global styles */
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: 'Roboto', system-ui, sans-serif;
  font-weight: 500;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Smooth scrolling */
html {
  scroll-behavior: smooth;
}

/* Focus styles for accessibility */
*:focus {
  outline: 2px solid #14b8a6;
  outline-offset: 2px;
}
</style>
