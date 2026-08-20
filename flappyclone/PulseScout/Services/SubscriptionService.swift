import Foundation
import Observation

protocol SubscriptionServicing: AnyObject {
    var tier: SubscriptionTier { get }
    func refresh() async
    func unlockInstantScout() async
    func restoreFree()
}

/// Demo storefront. Swap this implementation for RevenueCat (`Purchases.shared`) in production.
@Observable
final class SubscriptionService: SubscriptionServicing {
    private let defaults: UserDefaults
    private let storageKey = "pulsescout.subscriptionTier"

    private(set) var tier: SubscriptionTier

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
        if let raw = defaults.string(forKey: storageKey),
           let stored = SubscriptionTier(rawValue: raw) {
            self.tier = stored
        } else {
            self.tier = .free
        }
    }

    func refresh() async {
        // RevenueCat: `Purchases.shared.getCustomerInfo` → map entitlements["instant_scout"]
    }

    func unlockInstantScout() async {
        // RevenueCat: `Purchases.shared.purchase(package:)`
        setTier(.instantScout)
    }

    func restoreFree() {
        setTier(.free)
    }

    private func setTier(_ tier: SubscriptionTier) {
        self.tier = tier
        defaults.set(tier.rawValue, forKey: storageKey)
    }
}
