# PulseScout

iOS 17 SwiftUI app for watching **stocks** and **collectibles**, graphing recent prices, and firing local alerts when a move clears a custom percentage threshold.

Open `PulseScout.xcodeproj` in Xcode 15.3+, pick an iPhone simulator, and run.

## Features

- Watched-asset dashboard with category filters
- Mini SwiftUI Charts sparklines on every card
- Custom alert threshold (slider + 5% / 10% / 25% presets)
- Jump engine compares the last two price points and notifies when `|change| >= threshold`
- Blinking badge when an asset is currently over the threshold
- Free tier delays alerts (2–4 hours in Release, 15 seconds in Debug); Instant Scout is immediate
- Demo paywall at $4.99/mo — swap `SubscriptionService` for RevenueCat before shipping
- Mock live quotes for Apple, Tesla, Charizard ex, and Black Lotus

## Requirements

- macOS with Xcode 15.3 or later
- iOS 17 deployment target
- Apple Developer team (for device + TestFlight)

## Project layout

```
PulseScout/
  App/              App entry and root view
  Models/           Asset, alerts, subscription, mock data
  Services/         Jump math, live quotes, notifications, store stub
  ViewModels/       Dashboard and threshold screens
  Views/            Dashboard, charts, alerts, detail, paywall
  Theme/            Dark premium palette
  Resources/        Assets and Info.plist
PulseScoutTests/    Jump-engine unit tests
PulseScout.xcodeproj
project.yml         Optional XcodeGen spec
```

## How alerts work

`PriceJumpEngine` takes the last two `PricePoint` values on an asset:

```
percent = ((new - old) / |old|) * 100
```

If the absolute percent is at least the asset’s threshold, PulseScout schedules a `UserNotifications` local alert:

> 🚨 Price Jump! Charizard ex has spiked by 12.4%!

Free accounts schedule that notification after the delay. Instant Scout uses a near-zero interval.

Quotes currently come from `PriceMonitorService` (local random walk). Replace that service with a market/collectibles API when you have one.

## GitHub

This folder is a standalone iOS repo. From here:

```bash
git init
git add .
git commit -m "Initial commit: PulseScout iOS app"
gh repo create PulseScout --private --source=. --remote=origin --push
```

GitHub Actions (`.github/workflows/ios.yml`) builds and tests on `macos-14`.

If you add Swift files, regenerate the Xcode project:

```bash
python3 scripts/generate_xcodeproj.py
```

Or install [XcodeGen](https://github.com/yonaskolb/XcodeGen) and run `xcodegen`.

## RevenueCat (production)

`SubscriptionService` is a local stub so the UI can be tested without StoreKit. Before App Store release:

1. Add the RevenueCat SDK via SPM
2. Map entitlement `instant_scout` onto `SubscriptionTier.instantScout`
3. Replace `unlockInstantScout()` with `Purchases.shared.purchase(package:)`
4. Keep the 2–4 hour free delay in Release builds

## License

MIT
