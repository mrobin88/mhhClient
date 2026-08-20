import Foundation

enum PriceJumpEngine {
    /// Percentage change from `old` to `new`. Returns 0 when the previous price is 0.
    static func percentChange(from old: Double, to new: Double) -> Double {
        guard old != 0 else { return 0 }
        return ((new - old) / abs(old)) * 100
    }

    /// Change between the last two recorded price points.
    static func latestJump(in history: [PricePoint]) -> Double? {
        let points = history.sorted { $0.date < $1.date }
        guard points.count >= 2 else { return nil }
        return percentChange(from: points[points.count - 2].price, to: points[points.count - 1].price)
    }

    static func latestJump(for asset: Asset) -> Double? {
        latestJump(in: asset.history)
    }

    static func exceedsThreshold(_ jump: Double, threshold: Double) -> Bool {
        abs(jump) >= threshold && threshold > 0
    }

    static func evaluate(asset: Asset) -> PriceAlert? {
        guard asset.alertThresholdPercent > 0,
              let jump = latestJump(for: asset),
              exceedsThreshold(jump, threshold: asset.alertThresholdPercent) else {
            return nil
        }

        return PriceAlert(
            assetID: asset.id,
            assetName: asset.name,
            percentChange: jump,
            isDelayed: false
        )
    }
}
