import Foundation

enum AssetCategory: String, Codable, CaseIterable, Identifiable, Hashable {
    case stock
    case collectible

    var id: String { rawValue }

    var title: String {
        switch self {
        case .stock: return "Stocks"
        case .collectible: return "Collectibles"
        }
    }

    var singular: String {
        switch self {
        case .stock: return "Stock"
        case .collectible: return "Collectible"
        }
    }

    var systemImage: String {
        switch self {
        case .stock: return "chart.line.uptrend.xyaxis"
        case .collectible: return "rectangle.stack.fill"
        }
    }
}

struct PricePoint: Identifiable, Codable, Hashable {
    var id: UUID
    var date: Date
    var price: Double

    init(id: UUID = UUID(), date: Date, price: Double) {
        self.id = id
        self.date = date
        self.price = price
    }
}

struct Asset: Identifiable, Codable, Hashable {
    var id: UUID
    var name: String
    var symbol: String
    var category: AssetCategory
    var currentPrice: Double
    var currencyCode: String
    var history: [PricePoint]
    var alertThresholdPercent: Double
    var systemImage: String

    init(
        id: UUID = UUID(),
        name: String,
        symbol: String,
        category: AssetCategory,
        currentPrice: Double,
        currencyCode: String = "USD",
        history: [PricePoint] = [],
        alertThresholdPercent: Double = 5,
        systemImage: String
    ) {
        self.id = id
        self.name = name
        self.symbol = symbol
        self.category = category
        self.currentPrice = currentPrice
        self.currencyCode = currencyCode
        self.history = history
        self.alertThresholdPercent = alertThresholdPercent
        self.systemImage = systemImage
    }

    var sortedHistory: [PricePoint] {
        history.sorted { $0.date < $1.date }
    }

    var previousPrice: Double? {
        let points = sortedHistory
        guard points.count >= 2 else { return nil }
        return points[points.count - 2].price
    }

    var sessionChangePercent: Double {
        guard let first = sortedHistory.first?.price, first != 0 else { return 0 }
        return PriceJumpEngine.percentChange(from: first, to: currentPrice)
    }

    mutating func appendPrice(_ price: Double, at date: Date = .now) {
        currentPrice = price
        history.append(PricePoint(date: date, price: price))
        if history.count > 80 {
            history.removeFirst(history.count - 80)
        }
    }
}
