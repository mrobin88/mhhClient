<template>
  <div class="min-h-screen bg-gradient py-12 px-4">
    <!-- Header with organization branding -->
    <div class="max-w-5xl mx-auto mb-12 text-center">
      <div class="relative">
        <!-- Decorative background elements -->
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="w-24 h-24 border-4 border-mission-400 rounded-full opacity-20 animate-pulse"></div>
          <div class="w-12 h-12 border-2 border-mission-500 rounded-full absolute opacity-30 animate-ping"></div>
        </div>
        <h1 class="text-5xl font-bold text-slate-800 relative z-10 mb-4">
          <span class="text-mission-600">Client Services</span> Portal
        </h1>
        <p class="text-xl text-slate-600 relative z-10">Professional Service Management System</p>
        <div class="mt-4 flex justify-center space-x-2">
          <div class="w-2 h-2 bg-mission-400 rounded-full"></div>
          <div class="w-2 h-2 bg-mission-500 rounded-full"></div>
          <div class="w-2 h-2 bg-mission-600 rounded-full"></div>
        </div>
      </div>
    </div>

    <!-- Main Form Container -->
    <div class="max-w-5xl mx-auto">
      <form @submit.prevent="handleSubmit" class="form-card">
        <!-- Form Header -->
        <div class="form-header">
          <div class="decorative-pattern"></div>
          <div class="relative z-10">
            <h2 class="text-3xl font-bold text-white flex items-center mb-2">
              <svg class="w-10 h-10 mr-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              New Client Registration
            </h2>
            <p class="text-mission-100 text-lg">Complete the form below to register for services</p>
          </div>
        </div>

        <!-- Form Content -->
        <div class="p-10 space-y-10">
          <!-- Personal Information Section -->
          <div class="space-y-6">
            <div class="section-header">
              <div class="w-2 h-10 bg-mission-500 rounded-full mr-4"></div>
              <h3 class="text-2xl font-semibold text-slate-800">Personal Information</h3>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> First Name
                </label>
                <input 
                  v-model="form.first_name" 
                  type="text" 
                  required 
                  class="form-input"
                  placeholder="Enter first name"
                />
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">Middle Name</label>
                <input 
                  v-model="form.middle_name" 
                  type="text" 
                  class="form-input"
                  placeholder="Enter middle name"
                />
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> Last Name
                </label>
                <input 
                  v-model="form.last_name" 
                  type="text" 
                  required 
                  class="form-input"
                  placeholder="Enter last name"
                />
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> Date of Birth
                </label>
                <input 
                  v-model="form.dob" 
                  type="date" 
                  required 
                  class="form-input"
                />
                <p class="text-xs text-slate-500">mm/dd/yyyy</p>
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> Phone Number
                </label>
                <input 
                  v-model="form.phone" 
                  type="tel" 
                  required
                  class="form-input"
                  placeholder="(415) 555-0123"
                />
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">Email</label>
                <input 
                  v-model="form.email" 
                  type="email" 
                  class="form-input"
                  placeholder="name@example.com"
                />
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">SSN (Optional)</label>
                <input 
                  v-model="form.ssn" 
                  type="text" 
                  class="form-input"
                  placeholder="XXX-XX-XXXX"
                />
                <p class="text-xs text-slate-500">For employment verification only</p>
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> Gender
                </label>
                <select v-model="form.gender" required class="form-select">
                  <option disabled value="">Select gender</option>
                  <option value="M">Male</option>
                  <option value="F">Female</option>
                  <option value="NB">Non-binary</option>
                  <option value="O">Other</option>
                  <option value="P">Prefer not to say</option>
                </select>
              </div>
            </div>
          </div>

          <!-- Address Section -->
          <div class="space-y-6">
            <div class="section-header">
              <div class="w-2 h-10 bg-mission-500 rounded-full mr-4"></div>
              <h3 class="text-2xl font-semibold text-slate-800">Address</h3>
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-4 gap-8">
              <div class="lg:col-span-2 space-y-3">
                <label class="block text-sm font-semibold text-slate-700">Street Address</label>
                <input v-model="form.address" type="text" class="form-input" placeholder="123 Main St" />
              </div>
              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">City</label>
                <input v-model="form.city" type="text" class="form-input" placeholder="San Francisco" />
              </div>
              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">State</label>
                <input v-model="form.state" type="text" class="form-input" placeholder="CA" />
              </div>
              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">Zip</label>
                <input v-model="form.zip_code" type="text" class="form-input" placeholder="94103" />
              </div>
            </div>
          </div>

          <!-- San Francisco Residency & Demographics Section -->
          <div class="space-y-6">
            <div class="section-header">
              <div class="w-2 h-10 bg-mission-500 rounded-full mr-4"></div>
              <h3 class="text-2xl font-semibold text-slate-800">San Francisco Residency & Background</h3>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> San Francisco Resident
                </label>
                <select v-model="form.sf_resident" required class="form-select">
                  <option disabled value="">Select residency status</option>
                  <option value="yes">Yes, I live in San Francisco</option>
                  <option value="no">No, I live outside San Francisco</option>
                </select>
                <p class="text-xs text-slate-500">Priority given to SF residents</p>
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> Neighborhood/Area
                </label>
                <select v-model="form.neighborhood" required class="form-select">
                  <option disabled value="">Select your area</option>
                  <option value="mission">Mission District</option>
                  <option value="soma">South of Market (SoMa)</option>
                  <option value="bayview">Bayview-Hunters Point</option>
                  <option value="tenderloin">Tenderloin</option>
                  <option value="western">Western Addition</option>
                  <option value="other">Other San Francisco Area</option>
                </select>
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> Ethnicity/Race
                </label>
                <select v-model="form.demographic_info" required class="form-select">
                  <option disabled value="">Select ethnicity/race</option>
                  <option value="black">Black/African American</option>
                  <option value="white">White/Caucasian</option>
                  <option value="latinx">Hispanic/Latinx</option>
                  <option value="asian">Asian/Pacific Islander</option>
                  <option value="native">Native American</option>
                  <option value="mixed">Mixed Race</option>
                  <option value="other">Other</option>
                  <option value="prefer_not">Prefer not to say</option>
                </select>
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> Primary Language
                </label>
                <select v-model="form.language" required class="form-select">
                  <option disabled value="">Select primary language</option>
                  <option value="en">English</option>
                  <option value="es">Spanish</option>
                  <option value="zh">Chinese (Mandarin/Cantonese)</option>
                  <option value="vi">Vietnamese</option>
                  <option value="tl">Tagalog/Filipino</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div v-if="form.language === 'other'" class="lg:col-span-2 space-y-3">
                <label class="block text-sm font-semibold text-slate-700">Other Language</label>
                <input 
                  v-model="form.language_other" 
                  type="text" 
                  class="form-input"
                  placeholder="Please specify language"
                />
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> Education Level
                </label>
                <select v-model="form.highest_degree" required class="form-select">
                  <option disabled value="">Select highest education</option>
                  <option value="none">No formal education</option>
                  <option value="elementary">Elementary school</option>
                  <option value="middle">Middle school</option>
                  <option value="hs">High school diploma/GED</option>
                  <option value="some_college">Some college</option>
                  <option value="aa">Associate's degree (AA)</option>
                  <option value="ba">Bachelor's degree (BA/BS)</option>
                  <option value="ma">Master's degree (MA/MS)</option>
                  <option value="phd">Doctorate (PhD)</option>
                </select>
              </div>
            </div>
          </div>

          <!-- Employment & Training Section -->
          <div class="space-y-6">
            <div class="section-header">
              <div class="w-2 h-10 bg-mission-500 rounded-full mr-4"></div>
              <h3 class="text-2xl font-semibold text-slate-800">Employment & Training Interests</h3>
            </div>
            
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> Current Employment Status
                </label>
                <select v-model="form.employment_status" required class="form-select">
                  <option disabled value="">Select current status</option>
                  <option value="unemployed">Unemployed</option>
                  <option value="part_time">Part-time employment</option>
                  <option value="full_time">Full-time employment</option>
                  <option value="underemployed">Underemployed (seeking better job)</option>
                  <option value="student">Student</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div class="space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> Training Program Interest
                </label>
                <select v-model="form.training_interest" required class="form-select">
                  <option disabled value="">Select program of interest</option>
                  <option value="citybuild">CityBuild Academy</option>
                  <option value="citybuild_pro">CityBuild Pro | CAPSA</option>
                  <option value="security">Security Guard Card Program</option>
                  <option value="construction">Construction On Ramp</option>
                  <option value="pit_stop">Pit Stop Program</option>
                  <option value="general">General job readiness</option>
                  <option value="other">Other training</option>
                </select>
              </div>

              <!-- Pit Stop Specific Fields -->
              <div v-if="form.training_interest === 'pit_stop'" class="lg:col-span-2 space-y-6 p-6 border rounded-xl bg-slate-50">
                <h4 class="text-xl font-semibold text-slate-800">Pit Stop Application</h4>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label class="form-label">Are you legally able to work in the U.S.?</label>
                    <select v-model="pitstop.can_work_us" class="form-select">
                      <option :value="true">Yes</option>
                      <option :value="false">No</option>
                    </select>
                  </div>
                  <div>
                    <label class="form-label">Are you a veteran?</label>
                    <select v-model="pitstop.is_veteran" class="form-select">
                      <option :value="false">No</option>
                      <option :value="true">Yes</option>
                    </select>
                  </div>
                  <div>
                    <label class="form-label">Position you are applying for</label>
                    <input v-model="pitstop.position_applied_for" type="text" class="form-input" placeholder="Pit Stop Attendant" />
                  </div>
                  <div>
                    <label class="form-label">Available Start Date</label>
                    <input v-model="pitstop.available_start_date" type="date" class="form-input" />
                  </div>
                  <div>
                    <label class="form-label">Employment desired</label>
                    <div class="flex gap-4">
                      <label class="inline-flex items-center"><input type="radio" value="full_time" v-model="pitstop.employment_desired" class="mr-2"/> Full-time</label>
                      <label class="inline-flex items-center"><input type="radio" value="part_time" v-model="pitstop.employment_desired" class="mr-2"/> Part-time</label>
                      <label class="inline-flex items-center"><input type="radio" value="relief_list" v-model="pitstop.employment_desired" class="mr-2"/> Relief List</label>
                    </div>
                  </div>
                </div>
                <div>
                  <label class="form-label">Weekly Schedule Availability</label>
                  <div class="space-y-4">
                    <div v-for="day in days" :key="day" class="bg-white p-4 rounded border">
                      <div class="flex items-center mb-3">
                        <input 
                          type="checkbox" 
                          :id="'day-' + day"
                          :checked="isDaySelected(day)"
                          @change="toggleDay(day)"
                          class="mr-3 h-4 w-4 text-blue-600"
                        />
                        <label :for="'day-' + day" class="text-lg font-semibold">{{ day }}</label>
                      </div>
                      <div v-if="isDaySelected(day)" class="ml-7 grid grid-cols-2 md:grid-cols-4 gap-2">
                        <label v-for="shift in shifts" :key="shift.value" class="inline-flex items-center text-sm">
                          <input 
                            type="checkbox" 
                            :value="shift.value"
                            :checked="isTimeSelectedForDay(day, shift.value)"
                            @change="toggleTimeForDay(day, shift.value)"
                            class="mr-2 h-3 w-3 text-blue-600"
                          />
                          {{ shift.label }}
                        </label>
                      </div>
                    </div>
                  </div>
                </div>
                <div>
                  <label class="form-label">Employment History (Last Job)</label>
                  <div class="p-4 bg-white rounded border space-y-3 mb-3">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <input v-model="pitstop.employment_history[0].company" class="form-input" placeholder="Company name" />
                      <input v-model="pitstop.employment_history[0].title" class="form-input" placeholder="Job title/role" />
                      <input v-model="pitstop.employment_history[0].city" class="form-input" placeholder="City" />
                      <input v-model="pitstop.employment_history[0].state" class="form-input" placeholder="State" />
                      <input v-model="pitstop.employment_history[0].manager" class="form-input" placeholder="Manager name" />
                      <input v-model="pitstop.employment_history[0].phone" class="form-input" placeholder="Manager phone" />
                      <input v-model="pitstop.employment_history[0].start_date" type="date" class="form-input" />
                      <input v-model="pitstop.employment_history[0].end_date" type="date" class="form-input" />
                    </div>
                    <textarea v-model="pitstop.employment_history[0].responsibilities" class="form-input" rows="2" placeholder="Responsibilities"></textarea>
                  </div>
                </div>
                <div>
                  <label class="form-label">Education History</label>
                  <textarea v-model="pitstop.education_history" class="form-input" rows="3" placeholder="Schools, certifications, etc."></textarea>
                </div>
              </div>

              <div class="lg:col-span-2 space-y-3">
                <label class="block text-sm font-semibold text-slate-700">
                  <span class="text-mission-600">*</span> How did you hear about us?
                </label>
                <select v-model="form.referral_source" required class="form-select">
                  <option disabled value="">Select referral source</option>
                  <option value="friend">Friend or family member</option>
                  <option value="social_media">Social media</option>
                  <option value="website">Website search</option>
                  <option value="job_center">Job center/Workforce development</option>
                  <option value="community_org">Community organization</option>
                  <option value="walk_in">Walk-in visit</option>
                  <option value="other">Other</option>
                </select>
              </div>

              <div class="lg:col-span-2 space-y-3">
                <label class="block text-sm font-semibold text-slate-700">Additional Notes</label>
                <textarea 
                  v-model="form.additional_notes" 
                  class="form-input"
                  rows="3"
                  placeholder="Please share any additional information about your employment goals, barriers, or special circumstances..."
                ></textarea>
              </div>
            </div>
          </div>

          <!-- Resume Upload Section -->
          <div class="form-section">
            <div class="section-header">
              <div class="w-2 h-10 bg-mission-500 rounded-full mr-4"></div>
              <h3 class="text-xl font-semibold text-slate-800">Resume & Documents</h3>
            </div>
            
            <div class="form-group">
              <label class="form-label">
                Resume (Optional)
                <span class="text-slate-400 text-sm ml-2">PDF, Word, or text files accepted</span>
              </label>
              <input 
                type="file" 
                @change="handleFileUpload" 
                accept=".pdf,.doc,.docx,.txt"
                class="form-input file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-mission-100 file:text-mission-700 hover:file:bg-mission-200"
              />
              <p class="text-sm text-slate-600 mt-1">
                Upload your resume to help us better understand your skills and experience
              </p>
            </div>
          </div>

          <!-- Submit Section -->
          <div class="pt-8 border-t border-slate-200">
            <div class="flex flex-col lg:flex-row gap-6 items-center justify-between">
              <div class="text-sm text-slate-600">
                <span class="text-mission-600 font-semibold">*</span> Required fields
              </div>
              <button 
                type="submit" 
                class="submit-button group"
                :disabled="isSubmitting"
              >
                <svg v-if="isSubmitting" class="animate-spin -ml-1 mr-3 h-6 w-6 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <svg v-else class="w-6 h-6 mr-3" fill="currentColor" viewBox="0 0 20 20">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
                </svg>
                {{ isSubmitting ? 'Submitting...' : 'Submit Application' }}
              </button>
            </div>
          </div>

          <!-- Status Messages -->
          <div v-if="error" class="bg-red-50 border border-red-200 rounded-xl p-6">
            <div class="flex">
              <svg class="w-6 h-6 text-red-400 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
              </svg>
              <p class="text-red-800 font-medium">{{ error }}</p>
            </div>
          </div>

          <div v-if="success" class="bg-green-50 border border-green-200 rounded-xl p-6">
            <div class="flex">
              <svg class="w-6 h-6 text-green-400 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"/>
              </svg>
              <p class="text-green-800 font-medium">Application submitted successfully! We'll contact you within 2-3 business days.</p>
            </div>
          </div>
        </div>
      </form>
    </div>

    <!-- Footer with organization branding -->
    <div class="max-w-5xl mx-auto mt-12 text-center">
      <div class="flex justify-center space-x-3 mb-4">
        <div class="w-3 h-3 bg-mission-400 rounded-full animate-pulse"></div>
        <div class="w-2 h-2 bg-mission-500 rounded-full animate-ping"></div>
        <div class="w-3 h-3 bg-mission-600 rounded-full animate-pulse"></div>
      </div>
      <p class="text-slate-500 text-sm">Professional Client Services</p>
      <p class="text-slate-400 text-xs mt-2">Connecting people with opportunities</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { getApiUrl } from '../config/api'

const form = ref({
  first_name: '',
  middle_name: '',
  last_name: '',
  dob: '',
  ssn: '',
  phone: '',
  email: '',
  gender: '',
  address: '',
  city: '',
  state: '',
  zip_code: '',
  sf_resident: '',
  neighborhood: '',
  demographic_info: '',
  language: '',
  language_other: '',
  highest_degree: '',
  employment_status: '',
  training_interest: '',
  referral_source: '',
  additional_notes: '',
})

const days = ['Mon','Tue','Wed','Thu','Fri','Sat','Sun']
const shifts = [
  { value: '7-4', label: '7am-4pm' },
  { value: '8-5', label: '8am-5pm' },
  { value: '9-5', label: '9am-5pm' },
  { value: '10-7', label: '10am-7pm' },
  { value: '12-9', label: '12pm-9pm' },
  { value: '18-3', label: '6pm-3am' },
  { value: '21-6', label: '9pm-6am' },
  { value: '23-8', label: '11pm-8am' },
]

const pitstop = ref({
  can_work_us: false,
  is_veteran: false,
  position_applied_for: 'Pit Stop Attendant',
  available_start_date: '',
  employment_desired: 'full_time',
  weekly_schedule: {},
  employment_history: [
    { company: '', title: '', city: '', state: '', manager: '', phone: '', start_date: '', end_date: '', responsibilities: '' }
  ],
  education_history: '',
})

const resumeFile = ref(null)

const error = ref('')
const success = ref(false)
const isSubmitting = ref(false)

const handleFileUpload = (event) => {
  const file = event.target.files[0]
  if (file) {
    // Check file size (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      error.value = 'File size must be less than 5MB'
      event.target.value = ''
      return
    }
    
    // Check file type
    const allowedTypes = ['.pdf', '.doc', '.docx', '.txt']
    const fileExtension = '.' + file.name.split('.').pop().toLowerCase()
    if (!allowedTypes.includes(fileExtension)) {
      error.value = 'Please upload a PDF, Word, or text file'
      event.target.value = ''
      return
    }
    
    resumeFile.value = file
    error.value = ''
  }
}

// Schedule management methods
const isDaySelected = (day) => {
  return pitstop.value.weekly_schedule[day] && pitstop.value.weekly_schedule[day].length > 0
}

const isTimeSelectedForDay = (day, timeSlot) => {
  return pitstop.value.weekly_schedule[day] && pitstop.value.weekly_schedule[day].includes(timeSlot)
}

const toggleDay = (day) => {
  if (!pitstop.value.weekly_schedule[day] || pitstop.value.weekly_schedule[day].length === 0) {
    // Day not selected, select it with no time slots initially
    pitstop.value.weekly_schedule[day] = []
  } else {
    // Day is selected, deselect it
    delete pitstop.value.weekly_schedule[day]
  }
}

const toggleTimeForDay = (day, timeSlot) => {
  if (!pitstop.value.weekly_schedule[day]) {
    pitstop.value.weekly_schedule[day] = []
  }
  
  const index = pitstop.value.weekly_schedule[day].indexOf(timeSlot)
  if (index > -1) {
    // Time slot exists, remove it
    pitstop.value.weekly_schedule[day].splice(index, 1)
  } else {
    // Time slot doesn't exist, add it
    pitstop.value.weekly_schedule[day].push(timeSlot)
  }
}

async function handleSubmit() {
  error.value = ''
  success.value = false
  isSubmitting.value = true

  try {
    // Create FormData for file upload
    const formData = new FormData()
    
    // Add form fields
    Object.keys(form.value).forEach(key => {
      if (form.value[key] !== '') {
        formData.append(key, form.value[key])
      }
    })
    
    // Add resume file if selected
    if (resumeFile.value) {
      formData.append('resume', resumeFile.value)
    }
    
    const response = await axios.post(getApiUrl('/api/clients/'), formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    
    if (response.status === 201 || response.status === 200) {
      success.value = true
      
      // If Pit Stop, create related application
      if (form.value.training_interest === 'pit_stop') {
        const clientId = response.data.id
        try {
          await axios.post(getApiUrl('/api/pitstop-applications/'), {
            client: clientId,
            can_work_us: pitstop.value.can_work_us,
            is_veteran: pitstop.value.is_veteran,
            position_applied_for: pitstop.value.position_applied_for,
            available_start_date: pitstop.value.available_start_date || null,
            employment_desired: pitstop.value.employment_desired,
            weekly_schedule: pitstop.value.weekly_schedule,
            employment_history: pitstop.value.employment_history,
            education_history: pitstop.value.education_history,
          })
        } catch (pitstopError) {
          console.error('Pit Stop application submission failed:', pitstopError)
          console.error('Pit Stop data being sent:', {
            client: clientId,
            can_work_us: pitstop.value.can_work_us,
            is_veteran: pitstop.value.is_veteran,
            position_applied_for: pitstop.value.position_applied_for,
            available_start_date: pitstop.value.available_start_date || null,
            employment_desired: pitstop.value.employment_desired,
            weekly_schedule: pitstop.value.weekly_schedule,
            employment_history: pitstop.value.employment_history,
            education_history: pitstop.value.education_history,
          })
          // Don't throw error here - client was created successfully
          error.value = 'Client created successfully, but Pit Stop application failed to save. Please contact support.'
        }
      }

      // Reset form
      form.value = {
        first_name: '',
        middle_name: '',
        last_name: '',
        dob: '',
        ssn: '',
        phone: '',
        email: '',
        gender: '',
        address: '',
        city: '',
        state: '',
        zip_code: '',
        sf_resident: '',
        neighborhood: '',
        demographic_info: '',
        language: '',
        language_other: '',
        highest_degree: '',
        employment_status: '',
        training_interest: '',
        referral_source: '',
        additional_notes: '',
      }
      
      // Reset pitstop
      pitstop.value = {
        can_work_us: false,
        is_veteran: false,
        position_applied_for: 'Pit Stop Attendant',
        available_start_date: '',
        employment_desired: 'full_time',
        weekly_schedule: {},
        employment_history: [
          { company: '', title: '', city: '', state: '', manager: '', phone: '', start_date: '', end_date: '', responsibilities: '' }
        ],
        education_history: '',
      }

      // Reset resume file
      resumeFile.value = null
      
      // Reset file input
      const fileInput = document.querySelector('input[type="file"]')
      if (fileInput) fileInput.value = ''
    }
  } catch (err) {
    if (err.response?.status === 400) {
      error.value = 'Please check all required fields and try again.'
    } else if (err.response?.status === 409) {
      error.value = 'A client with this information already exists. Please contact us directly.'
    } else {
      error.value = 'Unable to submit application. Please try again or contact us at info@missionhiringhall.org'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
/* All styles are now handled by Tailwind CSS classes in style.css */
</style>
  