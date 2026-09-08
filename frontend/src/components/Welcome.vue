<template>
  <div
    class="welcome-shell min-h-[100dvh] min-w-full flex flex-col items-center justify-center px-5 py-12 sm:px-8 sm:py-16 text-slate-800 antialiased"
  >
    <div class="welcome-shell__grid pointer-events-none fixed inset-0 -z-10" aria-hidden="true" />
    <div class="welcome-shell__wash pointer-events-none fixed inset-0 -z-10" aria-hidden="true" />

    <div class="w-full max-w-2xl mx-auto flex flex-col items-center">
      <header class="text-center mb-10 sm:mb-12 w-full">
        <div class="relative">
          <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div class="w-24 h-24 border-4 border-mission-400 rounded-full opacity-20 animate-pulse"></div>
            <div class="w-12 h-12 border-2 border-mission-500 rounded-full absolute opacity-30 animate-ping"></div>
          </div>
          <h1 class="text-5xl font-bold text-slate-800 relative z-10 mb-4">
            <span class="text-mission-600">Welcome</span>
          </h1>
          <p class="text-xl text-slate-600 relative z-10">Mission Hiring Hall</p>
          <p class="mt-4 text-base sm:text-lg text-slate-600 leading-relaxed max-w-xl mx-auto font-medium px-2 relative z-10">
            Choose what you need today. New here? Sign up. Already with us? Check in.
          </p>
        </div>
      </header>

      <article
        class="welcome-card w-full rounded-xl border border-slate-200/90 bg-white overflow-hidden"
      >
        <div class="h-1.5 w-full bg-gradient-to-r from-mission-600 via-mission-500 to-mission-600" aria-hidden="true" />
        <div class="px-6 sm:px-8 pt-6 pb-2 border-b border-slate-100 bg-slate-50/80">
          <h2 class="text-xs sm:text-sm font-bold tracking-[0.18em] uppercase text-slate-500">Get started</h2>
        </div>
        <div class="p-6 sm:p-8 space-y-4">
          <RouterLink
            to="/checkin"
            class="welcome-choice welcome-choice-primary"
          >
            <span class="welcome-choice-kicker">I already have a profile</span>
            <span class="welcome-choice-title">Check In</span>
            <span class="welcome-choice-hint">Tell us you are here for a visit.</span>
          </RouterLink>
          <RouterLink
            to="/signup"
            class="welcome-choice welcome-choice-secondary"
          >
            <span class="welcome-choice-kicker">First time here</span>
            <span class="welcome-choice-title">Sign Up</span>
            <span class="welcome-choice-hint">Create a new client profile to get started.</span>
          </RouterLink>
        </div>
      </article>
    </div>
  </div>
</template>

<style scoped>
.welcome-shell {
  background: linear-gradient(to bottom right, #f0fdfa, #e2f8f4, #ccfbf1);
}

.welcome-shell__grid {
  background-image:
    linear-gradient(rgba(15, 118, 110, 0.06) 1px, transparent 1px),
    linear-gradient(90deg, rgba(15, 118, 110, 0.06) 1px, transparent 1px);
  background-size: 48px 48px;
  mask-image: radial-gradient(ellipse 95% 80% at 50% 20%, black 15%, transparent 65%);
  opacity: 0.5;
}

.welcome-shell__wash {
  background: radial-gradient(ellipse 120% 70% at 50% 0%, rgba(255, 255, 255, 0.75), transparent 55%);
}

.welcome-card {
  box-shadow:
    0 0 0 1px rgba(255, 255, 255, 0.8) inset,
    0 20px 50px -12px rgba(15, 118, 110, 0.15);
}

.welcome-choice {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  width: 100%;
  border-radius: 0.9rem;
  padding: 1.15rem 1.25rem;
  text-decoration: none;
  transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease, background-color 0.15s ease;
}

.welcome-choice-kicker {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.welcome-choice-title {
  font-size: 1.55rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.welcome-choice-hint {
  font-size: 0.95rem;
  font-weight: 500;
  line-height: 1.4;
}

.welcome-choice-primary {
  background: #0d9488;
  color: #fff;
  box-shadow: 0 1px 2px rgba(15, 118, 110, 0.2);
}

.welcome-choice-primary .welcome-choice-kicker,
.welcome-choice-primary .welcome-choice-hint {
  color: rgba(255, 255, 255, 0.86);
}

.welcome-choice-primary:hover {
  background: #0f766e;
  transform: translateY(-1px);
}

.welcome-choice-secondary {
  background: #fff;
  color: #0f172a;
  border: 2px solid #cbd5e1;
}

.welcome-choice-secondary .welcome-choice-kicker {
  color: #0f766e;
}

.welcome-choice-secondary .welcome-choice-hint {
  color: #475569;
}

.welcome-choice-secondary:hover {
  border-color: #0d9488;
  background: #f0fdfa;
}

@media (prefers-reduced-motion: reduce) {
  .welcome-choice {
    transition: none;
  }
}
</style>
