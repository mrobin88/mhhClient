<template>
  <div class="registration-page min-h-screen bg-gradient py-6 px-4 sm:py-10">
    <!-- Header with organization branding -->
    <div class="registration-shell mx-auto mb-6 text-center sm:mb-10">
      <div class="relative">
        <!-- Decorative background elements -->
        <div class="absolute inset-0 flex items-center justify-center">
          <div class="w-24 h-24 border-4 border-mission-400 rounded-full opacity-20 animate-pulse"></div>
          <div class="w-12 h-12 border-2 border-mission-500 rounded-full absolute opacity-30 animate-ping"></div>
        </div>
        <h1 class="registration-title font-bold text-slate-800 relative z-10 mb-3">
          <span class="text-mission-600">Client Services</span> Portal
        </h1>
        <p class="registration-subtitle text-slate-600 relative z-10">Professional Service Management System</p>
        <p class="text-mission-800 relative z-10 mt-3 text-base">
          Already registered?
          <RouterLink to="/checkin" class="font-semibold underline hover:text-mission-900">Check in here</RouterLink>
        </p>

        <div class="mt-4 flex justify-center space-x-2">
          <div class="w-2 h-2 bg-mission-400 rounded-full"></div>
          <div class="w-2 h-2 bg-mission-500 rounded-full"></div>
          <div class="w-2 h-2 bg-mission-600 rounded-full"></div>
        </div>
      </div>
    </div>

    <!-- Main Form Container -->
    <div class="registration-shell mx-auto">
      <form @submit.prevent="handleSubmit" class="form-card registration-form">
        <!-- Form Header -->
        <div class="form-header">
          <div class="decorative-pattern"></div>
          <div class="relative z-10">
            <h2 class="form-title font-bold text-white flex items-center mb-2">
              <svg class="w-10 h-10 mr-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              New Client Registration
            </h2>
            <p class="text-mission-100 form-intro">Complete the form below to register for services</p>
          </div>
        </div>

        <!-- Form Content -->
        <div class="form-body space-y-8">
          <!-- Training Program Interest Section - Compact Button Rows -->
          <div class="space-y-4">
            <div class="section-header">
              <div class="w-2 h-10 bg-mission-500 rounded-full mr-4"></div>
              <h3 class="section-title font-semibold text-slate-800">Training Program Interest <span class="text-mission-600">*</span></h3>
            </div>
            
            <div class="program-stack">
                <button
                  type="button"
                  @click="form.training_interest = 'citybuild'"
                  :class="[
                    'program-btn-compact',
                    form.training_interest === 'citybuild' ? 'program-btn-active' : 'program-btn-inactive'
                  ]"
                >
                  <span class="mr-2">🏗️</span>
                  <span>CityBuild Academy</span>
                </button>

                <button
                  type="button"
                  @click="form.training_interest = 'citybuild_pro'"
                  :class="[
                    'program-btn-compact',
                    form.training_interest === 'citybuild_pro' ? 'program-btn-active' : 'program-btn-inactive'
                  ]"
                >
                  <span class="mr-2">⚡</span>
                  <span>CityBuild Pro | CAPSA</span>
                </button>

                <button
                  type="button"
                  @click="form.training_interest = 'security'"
                  :class="[
                    'program-btn-compact',
                    form.training_interest === 'security' ? 'program-btn-active' : 'program-btn-inactive'
                  ]"
                >
                  <span class="mr-2">🛡️</span>
                  <span>Security Guard Card</span>
                </button>

                <button
                  type="button"
                  @click="form.training_interest = 'construction'"
                  :class="[
                    'program-btn-compact',
                    form.training_interest === 'construction' ? 'program-btn-active' : 'program-btn-inactive'
                  ]"
                >
                  <span class="mr-2">🔨</span>
                  <span>Construction On Ramp</span>
                </button>

                <button
                  type="button"
                  @click="form.training_interest = 'pit_stop'"
                  :class="[
                    'program-btn-compact',
                    form.training_interest === 'pit_stop' ? 'program-btn-active' : 'program-btn-inactive'
                  ]"
                >
                  <span class="mr-2">🚻</span>
                  <span>Pit Stop Program</span>
                </button>

                <button
                  type="button"
                  @click="form.training_interest = 'general'"
                  :class="[
                    'program-btn-compact',
                    form.training_interest === 'general' ? 'program-btn-active' : 'program-btn-inactive'
                  ]"
                >
                  <span class="mr-2">💼</span>
                  <span>General Job Readiness</span>
                </button>

                <button
                  type="button"
                  @click="form.training_interest = 'other'"
                  :class="[
                    'program-btn-compact',
                    form.training_interest === 'other' ? 'program-btn-active' : 'program-btn-inactive'
                  ]"
                >
                  <span class="mr-2">✨</span>
                  <span>Other Programs</span>
                </button>
            </div>

              <!-- Validation message -->
              <p v-if="!form.training_interest && formAttempted" class="text-red-600 text-sm">
                Please select a program to continue
              </p>
            </div>

            <!-- Pit Stop section is shown later, after main application fields -->
          </div>

          <!-- Personal Information Section -->
          <div class="space-y-6">
            <div class="section-header">
              <div class="w-2 h-10 bg-mission-500 rounded-full mr-4"></div>
              <h3 class="section-title font-semibold text-slate-800">Personal Information</h3>
            </div>
            
            <div class="form-stack">
              <div class="form-field">
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

              <div class="form-field">
                <label class="block text-sm font-semibold text-slate-700">Middle Name</label>
                <input 
                  v-model="form.middle_name" 
                  type="text" 
                  class="form-input"
                  placeholder="Enter middle name"
                />
              </div>

              <div class="form-field">
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

              <div class="form-field">
                <label class="block text-sm font-semibold text-slate-700">Date of Birth</label>
                <input
                  v-model="form.dob"
                  type="text"
                  inputmode="numeric"
                  autocomplete="bday"
                  class="form-input"
                  placeholder="MM/DD/YYYY"
                  @blur="form.dob = normalizeDateInput(form.dob)"
                />
                <p class="text-xs text-slate-500">Type MM/DD/YYYY so you do not have to scroll back through years.</p>
              </div>

              <div class="form-field">
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

              <div class="form-field">
                <label class="block text-sm font-semibold text-slate-700">Email</label>
                <input 
                  v-model="form.email" 
                  type="email" 
                  class="form-input"
                  placeholder="name@example.com"
                />
              </div>

              <div class="form-field">
                <label class="block text-sm font-semibold text-slate-700">SSN (Optional)</label>
                <input 
                  v-model="form.ssn" 
                  type="text" 
                  class="form-input"
                  placeholder="XXX-XX-XXXX"
                />
                <p class="text-xs text-slate-500">For employment verification only</p>
              </div>

              <div class="form-field">
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
              <h3 class="section-title font-semibold text-slate-800">Address</h3>
            </div>
            <div class="form-stack">
              <div class="form-field">
                <label class="block text-sm font-semibold text-slate-700">Street Address</label>
                <input v-model="form.address" type="text" class="form-input" placeholder="123 Main St" autocomplete="street-address" />
              </div>
              <div class="form-field">
                <label class="block text-sm font-semibold text-slate-700">City</label>
                <input v-model="form.city" type="text" class="form-input" placeholder="San Francisco" autocomplete="address-level2" />
              </div>
              <div class="form-field">
                <label class="block text-sm font-semibold text-slate-700">State</label>
                <input v-model="form.state" type="text" class="form-input" placeholder="CA" autocomplete="address-level1" />
              </div>
              <div class="form-field">
                <label class="block text-sm font-semibold text-slate-700">Zip</label>
                <input v-model="form.zip_code" type="text" inputmode="numeric" class="form-input" placeholder="94103" autocomplete="postal-code" />
              </div>
            </div>
          </div>

          <!-- San Francisco Residency & Demographics Section -->
          <div class="space-y-6">
            <div class="section-header">
              <div class="w-2 h-10 bg-mission-500 rounded-full mr-4"></div>
              <h3 class="section-title font-semibold text-slate-800">San Francisco Residency & Background</h3>
            </div>
            
            <div class="form-stack">
              <div class="form-field">
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

              <div class="form-field">
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

              <div class="form-field">
                <label class="block text-sm fontibold text-slate-700">
                  <span class="text-mission-600">*</span> Ethnicity/Race
                </label>
                <select v-model="form.demographic_info" required class="form-select">
                  <option disabled value="">Select ethnicity/race</option>
                  <option value="american_indian">American Indian or Alaska Native</option>
                  <option value="asian">Asian</option>
                  <option value="black">Black or African American</option>
                  <option value="white">Caucasian or White</option>
                  <option value="hispanic_latinx">Hispanic or Latin X</option>
                  <option value="middle_eastern">Middle Eastern</option>
                  <option value="pacific_islander">Native Hawaiian or Other Pacific Islander</option>
                  <option value="other">Other</option>
                  <option value="decline_state">Decline to State</option>
                  <option value="multiracial">Multiracial</option>
                </select>
              </div>

              <div class="form-field">
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

              <div v-if="form.language === 'other'" class="form-field">
                <label class="block text-sm font-semibold text-slate-700">Other Language</label>
                <input 
                  v-model="form.language_other" 
                  type="text" 
                  class="form-input"
                  placeholder="Please specify language"
                />
              </div>

              <div class="form-field">
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

          <!-- Employment & Referral Section -->
          <div class="space-y-6">
            <div class="section-header">
              <div class="w-2 h-10 bg-mission-500 rounded-full mr-4"></div>
              <h3 class="section-title font-semibold text-slate-800">Employment & Referral Information</h3>
            </div>
            
            <div class="form-stack">
              <div class="form-field">
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

              <div class="form-field">
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

              <div class="form-field">
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
              <h3 class="section-title font-semibold text-slate-800">Resume & Documents</h3>
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

            <!-- Optional supporting documents -->
            <div class="mt-6">
              <p class="text-sm text-slate-700 font-semibold mb-3">Optional documents (you can upload now or later)</p>

              <div class="docs-well">
                <div class="docs-scroll">
                  <div class="doc-tile">
                    <div class="doc-title">Proof of SF Residency</div>
                    <div class="doc-subtitle">Utility bill, lease, mail</div>
                    <input type="file" class="doc-input" :accept="docAccept" @change="(e) => handleDocUpload(e, 'sf_residency')" />
                    <div v-if="docFiles.sf_residency" class="doc-filename">{{ docFiles.sf_residency.name }}</div>
                  </div>

                  <div class="doc-tile">
                    <div class="doc-title">High School Graduation</div>
                    <div class="doc-subtitle">Diploma or GED</div>
                    <input type="file" class="doc-input" :accept="docAccept" @change="(e) => handleDocUpload(e, 'hs_diploma')" />
                    <div v-if="docFiles.hs_diploma" class="doc-filename">{{ docFiles.hs_diploma.name }}</div>
                  </div>

                  <div class="doc-tile">
                    <div class="doc-title">Identification</div>
                    <div class="doc-subtitle">Any ID you have</div>
                    <input type="file" class="doc-input" :accept="docAccept" @change="(e) => handleDocUpload(e, 'id')" />
                    <div v-if="docFiles.id" class="doc-filename">{{ docFiles.id.name }}</div>
                  </div>

                  <div class="doc-tile">
                    <div class="doc-title">Photo Release Form</div>
                    <div class="doc-subtitle">Signed form</div>
                    <input type="file" class="doc-input" :accept="docAccept" @change="(e) => handleDocUpload(e, 'photo_release')" />
                    <div v-if="docFiles.photo_release" class="doc-filename">{{ docFiles.photo_release.name }}</div>
                  </div>

                  <div class="doc-tile">
                    <div class="doc-title">Additional Document</div>
                    <div class="doc-subtitle">Name it (optional)</div>
                    <input
                      v-model="otherDocName"
                      type="text"
                      class="form-input !py-2 !px-3 !text-sm mb-3"
                      placeholder="Example: OSHA card, certificate"
                    />
                    <input type="file" class="doc-input" :accept="docAccept" @change="(e) => handleDocUpload(e, 'other')" />
                    <div v-if="docFiles.other" class="doc-filename">{{ docFiles.other.name }}</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Pit Stop Specific Fields (shown after main application) -->
          <div v-if="form.training_interest === 'pit_stop'" class="space-y-6 p-6 border rounded-xl bg-slate-50">
            <h4 class="text-xl font-semibold text-slate-800">Pit Stop Application</h4>
            <div class="form-stack">
              <div class="form-field">
                <label class="form-label">Are you legally able to work in the U.S.?</label>
                <select v-model="pitstop.can_work_us" class="form-select">
                  <option :value="true">Yes</option>
                  <option :value="false">No</option>
                </select>
              </div>
              <div class="form-field">
                <label class="form-label">Are you a veteran?</label>
                <select v-model="pitstop.is_veteran" class="form-select">
                  <option :value="false">No</option>
                  <option :value="true">Yes</option>
                </select>
              </div>
              <div class="form-field">
                <label class="form-label">Position you are applying for</label>
                <input v-model="pitstop.position_applied_for" type="text" class="form-input" placeholder="Pit Stop Attendant" />
              </div>
              <div class="form-field">
                <label class="form-label">Available Start Date</label>
                <input v-model="pitstop.available_start_date" type="date" class="form-input" />
              </div>
              <div class="form-field">
                <label class="form-label">Employment desired</label>
                <div class="mobile-checkbox-row flex gap-4">
                  <label class="inline-flex items-center"><input type="checkbox" value="full_time" v-model="pitstop.employment_desired" class="mr-2"/> Full-time</label>
                  <label class="inline-flex items-center"><input type="checkbox" value="part_time" v-model="pitstop.employment_desired" class="mr-2"/> Part-time</label>
                  <label class="inline-flex items-center"><input type="checkbox" value="relief_list" v-model="pitstop.employment_desired" class="mr-2"/> Relief List</label>
                </div>
              </div>
            </div>
            <div>
              <div class="flex items-center justify-between mb-3">
                <div>
                  <label class="form-label">Weekly Schedule Availability</label>
                  <p class="text-xs text-slate-600">Select all available time slots</p>
                </div>
                <button
                  type="button"
                  @click="selectAllTimeSlots"
                  class="open-availability-btn px-4 py-2 text-sm font-medium text-mission-700 bg-mission-50 border border-mission-200 rounded-lg hover:bg-mission-100 hover:border-mission-300 transition-colors"
                >
                  ✓ Open Availability
                </button>
              </div>
              <div class="schedule-grid-wrap">
                <div class="schedule-days space-y-2">
                  <div v-for="day in days" :key="day" class="schedule-day bg-white p-2.5 rounded-lg border border-slate-200">
                    <div class="schedule-day-grid grid grid-cols-[100px_1fr] gap-3 items-center">
                      <span class="text-sm font-semibold text-slate-700">{{ day }}</span>
                      <div class="schedule-slot-grid grid grid-cols-3 gap-2">
                        <button
                          v-for="shift in shifts"
                          :key="shift.value"
                          type="button"
                          @click="toggleTimeForDay(day, shift.value)"
                          :class="[
                            'time-slot-compact',
                            isTimeSelectedForDay(day, shift.value) ? 'time-slot-active' : 'time-slot-inactive'
                          ]"
                          :title="shift.label"
                        >
                          <span class="font-semibold">{{ shift.value }}</span>
                          <span class="text-[10px] block leading-tight opacity-75">{{ getShiftLabel(shift.value) }}</span>
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div>
              <label class="form-label">Employment History (Last Job)</label>
              <div class="p-4 bg-white rounded border space-y-3 mb-3">
                <div class="form-stack">
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
    <div class="registration-shell mx-auto mt-8 text-center sm:mt-12">
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

const days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
const shifts = [
  { value: '7-4', label: '7:00AM - 4:00PM' },
  { value: '8-5', label: '8:00AM - 5:00PM' },
  { value: '9-6', label: '9:00AM - 6:00PM' },
  { value: '10-7', label: '10:00AM - 7:00PM' },
  { value: '11-8', label: '11:00AM - 8:00PM' },
  { value: '12-9', label: '12:00PM - 9:00PM' },
  { value: '18-3', label: '6:00PM - 3:00AM' },
  { value: '21-6', label: '9:00PM - 6:00AM' },
  { value: '23-8', label: '11:00PM - 8:00AM' },
]

const pitstop = ref({
  can_work_us: false,
  is_veteran: false,
  position_applied_for: 'Pit Stop Attendant',
  available_start_date: '',
  employment_desired: [],
  weekly_schedule: {},
  employment_history: [
    { company: '', title: '', city: '', state: '', manager: '', phone: '', start_date: '', end_date: '', responsibilities: '' }
  ],
  education_history: '',
})

const resumeFile = ref(null)
const docAccept = '.pdf,.doc,.docx,.jpg,.jpeg,.png,.txt'
const docFiles = ref({
  sf_residency: null,
  hs_diploma: null,
  id: null,
  photo_release: null,
  other: null,
})
const otherDocName = ref('')

const error = ref('')
const success = ref(false)
const isSubmitting = ref(false)
const formAttempted = ref(false)

const MAX_TOTAL_UPLOAD_BYTES = 20 * 1024 * 1024 // 20MB total across resume + optional docs
const MAX_DOC_IMAGE_DIMENSION = 1600
const MAX_DOC_IMAGE_BYTES = 2 * 1024 * 1024

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

const fileNameWithExtension = (originalName, extension) => {
  const idx = originalName.lastIndexOf('.')
  if (idx <= 0) return `${originalName}${extension}`
  return `${originalName.slice(0, idx)}${extension}`
}

const readFileAsDataUrl = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(new Error('Failed to read file'))
    reader.readAsDataURL(file)
  })

const loadImageFromDataUrl = (dataUrl) =>
  new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve(img)
    img.onerror = () => reject(new Error('Failed to load image'))
    img.src = dataUrl
  })

const compressImageFile = async (file) => {
  const dataUrl = await readFileAsDataUrl(file)
  const image = await loadImageFromDataUrl(dataUrl)

  const width = image.width || 1
  const height = image.height || 1
  const scale = Math.min(1, MAX_DOC_IMAGE_DIMENSION / Math.max(width, height))
  const targetWidth = Math.max(1, Math.round(width * scale))
  const targetHeight = Math.max(1, Math.round(height * scale))

  const canvas = document.createElement('canvas')
  canvas.width = targetWidth
  canvas.height = targetHeight
  const context = canvas.getContext('2d')
  if (!context) return file
  context.drawImage(image, 0, 0, targetWidth, targetHeight)

  let quality = 0.82
  let bestBlob = null

  // Use JPEG for camera/photo uploads to reduce payload size.
  for (let i = 0; i < 4; i += 1) {
    // eslint-disable-next-line no-await-in-loop
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality))
    if (!blob) break
    bestBlob = blob
    if (blob.size <= MAX_DOC_IMAGE_BYTES) break
    quality -= 0.12
  }

  if (!bestBlob || bestBlob.size >= file.size) return file
  return new File([bestBlob], fileNameWithExtension(file.name, '.jpg'), {
    type: 'image/jpeg',
    lastModified: Date.now(),
  })
}

const handleDocUpload = async (event, key) => {
  const file = event.target.files[0]
  if (!file) return

  let processedFile = file

  if ((file.type || '').startsWith('image/')) {
    try {
      processedFile = await compressImageFile(file)
    } catch (compressionError) {
      console.warn('Image compression skipped:', compressionError)
      processedFile = file
    }
  }

  // Max 8MB for supporting docs
  if (processedFile.size > 8 * 1024 * 1024) {
    error.value = 'Document file size must be less than 8MB'
    event.target.value = ''
    return
  }

  const allowedExtensions = ['.pdf', '.doc', '.docx', '.txt', '.jpg', '.jpeg', '.png', '.webp', '.heic', '.heif']
  const ext = '.' + processedFile.name.split('.').pop().toLowerCase()
  if (!allowedExtensions.includes(ext)) {
    error.value = 'Please upload PDF, Word, image, or text files'
    event.target.value = ''
    return
  }

  docFiles.value[key] = processedFile
  error.value = ''
}

// Weekly schedule: multiple selections per day
const isTimeSelectedForDay = (day, value) => {
  const slots = pitstop.value.weekly_schedule[day] || []
  return slots.includes(value)
}

const toggleTimeForDay = (day, value) => {
  const current = pitstop.value.weekly_schedule[day] || []
  const idx = current.indexOf(value)
  if (idx >= 0) {
    current.splice(idx, 1)
  } else {
    current.push(value)
  }
  if (current.length === 0) {
    delete pitstop.value.weekly_schedule[day]
  } else {
    pitstop.value.weekly_schedule[day] = [...current]
  }
}

const selectAllTimeSlots = () => {
  // Get all shift values
  const allShiftValues = shifts.map(shift => shift.value)
  
  // Set all shifts for all days
  days.forEach(day => {
    pitstop.value.weekly_schedule[day] = [...allShiftValues]
  })
}

const getShiftLabel = (value) => {
  const labels = {
    '7-4': '7am-4pm',
    '8-5': '8am-5pm',
    '9-6': '9am-6pm',
    '10-7': '10am-7pm',
    '11-8': '11am-8pm',
    '12-9': '12pm-9pm',
    '18-3': '6pm-3am',
    '21-6': '9pm-6am',
    '23-8': '11pm-8am',
  }
  return labels[value] || value
}

const normalizeDateInput = (value) => {
  const raw = String(value || '').trim()
  if (!raw) return ''

  if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw

  const digits = raw.replace(/\D/g, '')
  if (digits.length !== 8) return raw

  const month = digits.slice(0, 2)
  const day = digits.slice(2, 4)
  const year = digits.slice(4, 8)
  const candidate = new Date(`${year}-${month}-${day}T12:00:00`)

  if (
    Number.isNaN(candidate.getTime()) ||
    candidate.getFullYear() !== Number(year) ||
    candidate.getMonth() + 1 !== Number(month) ||
    candidate.getDate() !== Number(day)
  ) {
    return raw
  }

  return `${year}-${month}-${day}`
}

const getResponseErrorMessage = (response) => {
  const status = response?.status
  const data = response?.data

  if (status === 413) {
    return 'Upload is too large. Please use smaller files and try again.'
  }
  if (status === 429) {
    return 'Too many attempts. Please wait a minute and try again.'
  }

  if (typeof data?.detail === 'string' && data.detail.trim()) {
    return data.detail
  }
  if (typeof data?.message === 'string' && data.message.trim()) {
    return data.message
  }
  if (data && typeof data === 'object') {
    const firstEntry = Object.entries(data).find(([, value]) => {
      if (Array.isArray(value)) return value.length > 0
      return typeof value === 'string' && value.trim()
    })
    if (firstEntry) {
      const [field, value] = firstEntry
      if (Array.isArray(value)) {
        return `${field}: ${String(value[0])}`
      }
      return `${field}: ${String(value)}`
    }
  }

  return 'Unable to submit application. Please check your information and try again.'
}

async function handleSubmit() {
  formAttempted.value = true
  error.value = ''
  success.value = false
  isSubmitting.value = true

  try {
    const selectedFiles = [
      resumeFile.value,
      docFiles.value.sf_residency,
      docFiles.value.hs_diploma,
      docFiles.value.id,
      docFiles.value.photo_release,
      docFiles.value.other,
    ].filter(Boolean)

    const totalBytes = selectedFiles.reduce((sum, file) => sum + (file?.size || 0), 0)
    if (totalBytes > MAX_TOTAL_UPLOAD_BYTES) {
      error.value = 'Total upload size is too large (max 20MB combined). Please remove one file or upload smaller files.'
      return
    }

    // Create FormData for file upload
    const formData = new FormData()
    
    // Add form fields
    Object.keys(form.value).forEach(key => {
      if (form.value[key] !== '') {
        const value = key === 'dob' ? normalizeDateInput(form.value[key]) : form.value[key]
        formData.append(key, value)
      }
    })
    
    // Add resume file if selected
    if (resumeFile.value) {
      formData.append('resume', resumeFile.value)
    }

    // Add supporting documents (optional)
    if (docFiles.value.sf_residency) formData.append('doc_sf_residency', docFiles.value.sf_residency)
    if (docFiles.value.hs_diploma) formData.append('doc_hs_diploma', docFiles.value.hs_diploma)
    if (docFiles.value.id) formData.append('doc_id', docFiles.value.id)
    if (docFiles.value.photo_release) formData.append('doc_photo_release', docFiles.value.photo_release)
    if (docFiles.value.other) {
      formData.append('doc_other', docFiles.value.other)
      if (otherDocName.value.trim()) formData.append('doc_other_name', otherDocName.value.trim())
    }
    
    const url = getApiUrl('/api/clients/')
    console.log('[Submit] POST', url)
    const response = await axios.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      validateStatus: () => true
    })
    console.log('[Submit] Response', response.status, response.data)
    
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
        employment_desired: [],
        weekly_schedule: {},
        employment_history: [
          { company: '', title: '', city: '', state: '', manager: '', phone: '', start_date: '', end_date: '', responsibilities: '' }
        ],
        education_history: '',
      }

      // Reset resume file
      resumeFile.value = null
      docFiles.value = { sf_residency: null, hs_diploma: null, id: null, photo_release: null, other: null }
      otherDocName.value = ''
      
      // Reset file inputs
      const fileInputs = document.querySelectorAll('input[type="file"]')
      fileInputs.forEach((el) => {
        try { el.value = '' } catch (_) {}
      })
    } else {
      error.value = getResponseErrorMessage(response)
    }
  } catch (err) {
    // Network or CORS-layer errors (no response)
    console.error('[Submit] Error', err)
    if (err.response?.status === 409) {
      error.value = 'A client with this information already exists. Please contact us directly.'
    } else {
      error.value = getResponseErrorMessage(err.response) || 'Unable to submit application. Please try again or contact us at info@missionhiringhall.org'
    }
  } finally {
    isSubmitting.value = false
  }
}
</script>

<style scoped>
.registration-shell {
  width: 100%;
  max-width: 42rem;
}

.registration-title {
  font-size: clamp(1.75rem, 6vw, 3rem);
  line-height: 1.12;
}

.registration-subtitle {
  font-size: clamp(1rem, 3.5vw, 1.25rem);
  line-height: 1.45;
}

.form-title {
  font-size: clamp(1.35rem, 4.5vw, 1.875rem);
  line-height: 1.2;
}

.form-intro {
  font-size: clamp(0.95rem, 3.2vw, 1.125rem);
  line-height: 1.45;
}

.section-title {
  font-size: clamp(1.15rem, 4vw, 1.5rem);
  line-height: 1.25;
}

.form-body {
  padding: clamp(1rem, 4vw, 2.5rem);
}

.form-stack {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  width: 100%;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  width: 100%;
  min-width: 0;
}

.program-stack {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  width: 100%;
}

/* Program buttons — full-width tap targets for phones */
.program-btn-compact {
  width: 100%;
  padding: 0.9rem 1rem;
  border-radius: 0.75rem;
  border: 2px solid #e2e8f0;
  background: white;
  font-size: 1rem;
  font-weight: 600;
  color: #475569;
  transition: all 0.2s ease;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  text-align: left;
  line-height: 1.3;
  min-height: 3.1rem;
}

.program-btn-inactive {
  border-color: #e2e8f0;
  background: white;
  color: #475569;
}

.program-btn-inactive:hover {
  border-color: #14b8a6;
  background: #f0fdfa;
  color: #0d9488;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(20, 184, 166, 0.15);
}

.program-btn-active {
  border-color: #14b8a6;
  background: #14b8a6;
  color: white;
  box-shadow: 0 2px 8px rgba(20, 184, 166, 0.25);
}

.program-btn-active:hover {
  background: #0d9488;
  border-color: #0d9488;
}

.program-btn-compact:active {
  transform: scale(0.98);
}

/* Time Slot Compact Styles */
.time-slot-compact {
  padding: 0.5rem 0.625rem;
  border-radius: 0.5rem;
  border: 2px solid #e2e8f0;
  background: white;
  transition: all 0.15s ease;
  cursor: pointer;
  font-size: 0.75rem;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 3rem;
}

.time-slot-inactive {
  color: #64748b;
}

.time-slot-inactive:hover {
  border-color: #14b8a6;
  background: #f0fdfa;
  color: #0d9488;
  transform: translateY(-1px);
}

.time-slot-active {
  border-color: #14b8a6;
  background: #14b8a6;
  color: white;
}

.time-slot-compact:active {
  transform: scale(0.97);
}

.docs-well {
  border: 2px solid #e2e8f0;
  border-radius: 1rem;
  background: #f8fafc;
  padding: 0.75rem;
}

.docs-scroll {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  width: 100%;
}

.doc-tile {
  width: 100%;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 0.9rem;
  padding: 1rem;
}

.doc-title {
  font-weight: 800;
  color: #0f172a;
  font-size: 0.95rem;
}

.doc-subtitle {
  color: #64748b;
  font-size: 0.8rem;
  margin-top: 0.25rem;
  margin-bottom: 0.75rem;
}

.doc-input {
  width: 100%;
}

.doc-filename {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #0f766e;
  font-weight: 600;
  word-break: break-word;
}

textarea.form-input {
  display: block;
  min-height: 7rem;
  resize: vertical;
  line-height: 1.5;
}

.registration-form .form-input,
.registration-form .form-select {
  width: 100%;
  min-height: 3.1rem;
  font-size: 16px;
  padding: 0.85rem 0.95rem;
  box-sizing: border-box;
}

.registration-form select.form-select {
  line-height: 1.35;
}

.registration-form textarea.form-input {
  min-height: 8rem;
}

.registration-form input[type="file"] {
  width: 100%;
  font-size: 0.95rem;
}

.registration-form .section-header {
  align-items: flex-start;
  padding: 0.85rem;
  margin-bottom: 0.75rem;
}

.registration-form .section-header .w-2 {
  flex-shrink: 0;
}

.registration-form .mobile-checkbox-row {
  flex-direction: column;
  align-items: stretch;
  gap: 0.65rem;
}

.registration-form .mobile-checkbox-row label {
  min-height: 2.85rem;
  padding: 0.7rem 0.8rem;
  border: 1px solid #cbd5e1;
  border-radius: 0.75rem;
  background: #ffffff;
}

.registration-form .open-availability-btn {
  width: 100%;
  min-height: 2.85rem;
}

.schedule-grid-wrap {
  overflow: visible;
  width: 100%;
}

.schedule-day-grid {
  display: block;
}

.schedule-day-grid > span {
  display: block;
  margin-bottom: 0.65rem;
}

.schedule-slot-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
}

.registration-form .submit-button {
  width: 100%;
  min-height: 3.35rem;
  transform: none !important;
}

.registration-form .form-header {
  padding: clamp(1.1rem, 4vw, 2rem);
}

.registration-form .form-header svg {
  width: 1.75rem;
  height: 1.75rem;
  margin-right: 0.75rem;
  flex: none;
}

@media (min-width: 640px) {
  .schedule-slot-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>
  