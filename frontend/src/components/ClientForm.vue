<template>
    <form @submit.prevent="handleSubmit" class="max-w-3xl mx-auto p-4 space-y-4 bg-white rounded shadow">
      <h2 class="text-xl font-bold mb-4">Add New Client</h2>
  
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <!-- Existing fields -->
        <div class="flex items-center gap-4">
          <label class="block text-sm font-medium">First Name</label>
          <input v-model="form.first_name" type="text" required class="input" />
        </div>
  
        <div>
          <label class="block text-sm font-medium gap-y-4">Last Name</label>
          <input v-model="form.last_name" type="text" required class="input" />
        </div>
  
        <div>
          <label class="block text-sm font-medium">Date of Birth</label>
          <input v-model="form.dob" type="date" required class="input" />
        </div>
  
        <div>
          <label class="block text-sm font-medium">Phone</label>
          <input v-model="form.phone" type="tel" class="input" />
        </div>
  
        <div>
          <label class="block text-sm font-medium">SSN</label>
          <input v-model="form.ssn" type="text" class="input" />
        </div>
  
        <div>
          <label class="block text-sm font-medium">Gender</label>
          <select v-model="form.gender" required class="input">
            <option disabled value="">Select gender</option>
            <option value="M">Male</option>
            <option value="F">Female</option>
            <option value="NB">Non-binary</option>
            <option value="O">Other</option>
          </select>
        </div>
  
        <!-- New fields -->
  
        <div>
          <label class="block text-sm font-medium">Demographic Info</label>
          <select v-model="form.demographic_info" required class="input">
            <option disabled value="">Select demographic</option>
            <option value="black">Black</option>
            <option value="white">White</option>
            <option value="latinx">Latinx</option>
            <option value="asian">Asian</option>
            <option value="native">Native American</option>
            <option value="other">Other</option>
          </select>
        </div>
  
        <div>
          <label class="block text-sm font-medium">Language</label>
          <select v-model="form.language" required class="input">
            <option disabled value="">Select language</option>
            <option value="en">English</option>
            <option value="es">Spanish</option>
            <option value="other">Other</option>
          </select>
        </div>
  
        <div v-if="form.language === 'other'">
          <label class="block text-sm font-medium">Other Language</label>
          <input v-model="form.language_other" type="text" class="input" />
        </div>
  
        <div>
          <label class="block text-sm font-medium">Orientation</label>
          <select v-model="form.orientation" required class="input">
            <option disabled value="">Select orientation</option>
            <option value="straight">Straight</option>
            <option value="lgbtq+">LGBTQ+</option>
            <option value="other">Other</option>
          </select>
        </div>
  
        <div>
          <label class="block text-sm font-medium">Highest Degree</label>
          <select v-model="form.highest_degree" required class="input">
            <option disabled value="">Select degree</option>
            <option value="none">None</option>
            <option value="hs">High School</option>
            <option value="aa">AA</option>
            <option value="ba">BA</option>
            <option value="ma">MA</option>
            <option value="phd">PhD</option>
          </select>
        </div>
  
        <div>
          <label class="block text-sm font-medium">Employment Status</label>
          <input v-model="form.employment_status" type="text" required class="input" />
        </div>
  
        <div>
          <label class="block text-sm font-medium">Staff Name</label>
          <input v-model="form.staff_name" type="text" required class="input" />
        </div>
  
        <div>
          <label class="block text-sm font-medium">Nonprofit</label>
          <input v-model="form.nonprofit" type="text" required class="input" />
        </div>
      </div>
  
      <div>
        <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          Submit
        </button>
      </div>
  
      <p v-if="error" class="text-red-500">{{ error }}</p>
      <p v-if="success" class="text-green-600">Client saved successfully!</p>
    </form>
  </template>
  
  <script setup>
  import { ref } from 'vue'
  import axios from 'axios'
  
  const form = ref({
    first_name: '',
    last_name: '',
    dob: '',
    ssn: '',
    phone: '',
    gender: '',
  
    demographic_info: '',
    language: '',
    language_other: '',
    orientation: '',
    highest_degree: '',
    employment_status: '',
    staff_name: '',
    nonprofit: '',
  })
  
  const error = ref('')
  const success = ref(false)
  
  async function handleSubmit() {
    error.value = ''
    success.value = false
  
    try {
      const response = await axios.post('http://localhost:8000/api/clients/', form.value)
      if (response.status === 201 || response.status === 200) {
        success.value = true
        form.value = {
          first_name: '',
          last_name: '',
          dob: '',
          ssn: '',
          phone: '',
          gender: '',
          demographic_info: '',
          language: '',
          language_other: '',
          orientation: '',
          highest_degree: '',
          employment_status: '',
          staff_name: '',
          nonprofit: '',
        }
      }
    } catch (err) {
      if (err.response?.status === 400) {
        error.value = 'Validation error: please check input fields.'
      } else if (err.response?.status === 409) {
        error.value = 'A client with this SSN or phone already exists.'
      } else {
        error.value = 'Failed to save client. Try again.'
      }
    }
  }
  </script>
  
  <style scoped>
  .input {
    @apply w-full border border-gray-300 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400;
  }
  </style>
  