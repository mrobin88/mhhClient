import Foundation

struct AlertConfiguration: Codable, Equatable {
    var thresholdPercent: Double
    var isEnabled: Bool

    static let `default` = AlertConfiguration(thresholdPercent: 5, isEnabled: true)

    static let presets: [Double] = [5, 10, 25]
}

struct PriceAlert: Identifiable, Codable, Equatable {
    var id: UUID
    var assetID: UUID
    var assetName: String
    var percentChange: Double
    var triggeredAt: Date
    var deliveredAt: Date?
    var isDelayed: Bool

    init(
        id: UUID = UUID(),
        assetID: UUID,
        assetName: String,
        percentChange: Double,
        triggeredAt: Date = .now,
        deliveredAt: Date? = nil,
        isDelayed: Bool
    ) {
        self.id = id
        self.assetID = assetID
        self.assetName = assetName
        self.percentChange = percentChange
        self.triggeredAt = triggeredAt
        self.deliveredAt = deliveredAt
        self.isDelayed = isDelayed
    }

    var isSpike: Bool { percentChange > 0 }

    var headline: String {
        let amount = String(format: "%.1f", abs(percentChange))
        if isSpike {
            return "Price Jump! \(assetName) has spiked by \(amount)%!"
        }
        return "Price Drop! \(assetName) has fallen by \(amount)%!"
    }
}
