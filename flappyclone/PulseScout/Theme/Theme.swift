import SwiftUI

enum Theme {
    static let background = Color(red: 0.035, green: 0.043, blue: 0.07)
    static let card = Color(red: 0.09, green: 0.11, blue: 0.165)
    static let cardElevated = Color(red: 0.12, green: 0.14, blue: 0.21)
    static let border = Color.white.opacity(0.08)
    static let textPrimary = Color.white
    static let textSecondary = Color.white.opacity(0.62)
    static let textMuted = Color.white.opacity(0.38)

    static let gain = Color(red: 0.22, green: 0.95, blue: 0.66)
    static let loss = Color(red: 1.0, green: 0.33, blue: 0.48)
    static let gold = Color(red: 0.97, green: 0.78, blue: 0.28)
    static let accent = Color(red: 0.51, green: 0.45, blue: 1.0)
    static let stock = Color(red: 0.38, green: 0.74, blue: 1.0)
    static let collectible = Color(red: 1.0, green: 0.58, blue: 0.28)

    static func color(for category: AssetCategory) -> Color {
        switch category {
        case .stock: return stock
        case .collectible: return collectible
        }
    }

    static func trendColor(_ change: Double) -> Color {
        change >= 0 ? gain : loss
    }
}
