import Foundation
import Observation

@MainActor
@Observable
final class AlertSettingsViewModel {
    var threshold: Double
    var applyToAll: Bool

    let presets = AlertConfiguration.presets
    let range: ClosedRange<Double> = 1...50

    init(initialThreshold: Double, applyToAll: Bool = false) {
        self.threshold = Self.clamped(initialThreshold)
        self.applyToAll = applyToAll
    }

    var formattedThreshold: String {
        String(format: "%.0f%%", threshold)
    }

    func selectPreset(_ value: Double) {
        threshold = Self.clamped(value)
    }

    func commit(to dashboard: DashboardViewModel, assetID: UUID?) {
        let value = Self.clamped(threshold)
        if applyToAll || assetID == nil {
            dashboard.applyThresholdToAll(value)
        } else if let assetID {
            dashboard.updateThreshold(value, for: assetID)
        }
    }

    private static func clamped(_ value: Double) -> Double {
        min(50, max(1, value.rounded()))
    }
}
