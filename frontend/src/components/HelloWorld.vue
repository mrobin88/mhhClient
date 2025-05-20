<template>
  <form @submit.prevent="submitForm" class="space-y-4 p-4 border rounded-md shadow">
    <div>
      <label class="block text-sm font-medium text-gray-700">Full Name</label>
      <input v-model="form.name" class="input" type="text" required />
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700">Phone</label>
      <input v-model="form.phone" class="input" type="tel" required />
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700">SSN</label>
      <input v-model="form.ssn" class="input" type="text" />
    </div>

    <div v-if="error" class="text-red-600">{{ error }}</div>

    <button type="submit" class="bg-blue-500 text-white py-2 px-4 rounded hover:bg-blue-600">
      Save Client
    </button>
  </form>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import axios from 'axios'

const form = ref({
  name: '',
  phone: '',
  ssn: '',
})

const error = ref<string | null>(null)

const submitForm = async () => {
  error.value = null
  try {
    const response = await axios.post('/api/clients/', form.value)
    alert('Client saved!')
    form.value = { name: '', phone: '', ssn: '' }
  } catch (err: any) {
    if (err.response && err.response.data) {
      error.value = Object.values(err.response.data).join(', ')
    } else {
      error.value = 'Something went wrong'
    }
  }
}
</script>

<style scoped>
.input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ccc;
  border-radius: 0.375rem;
}
</style>

