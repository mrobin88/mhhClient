import Foundation

enum SubscriptionTier: String, Codable, CaseIterable, Identifiable {
    case free
    case instantScout

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .free: return "Free"
        case .instantScout: return "Instant Scout"
        }
    }

    var monthlyPrice: String {
        switch self {
        case .free: return "$0"
        case .instantScout: return "$4.99"
        }
    }

    /// Production delay is 2–4 hours for Free. Debug uses 15s so the delay tactic is testable.
    var alertDelay: TimeInterval {
        switch self {
        case .free:
            #if DEBUG
            return 15
            #else
            return 3 * 60 * 60
            #endif
        case .instantScout:
            return 0
        }
    }

    var delayCopy: String {
        switch self {
        case .free: return "Alerts delayed 2–4 hours"
        case .instantScout: return "Real-time alerts"
        }
    }
}
