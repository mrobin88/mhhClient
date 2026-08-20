import Foundation

enum MockData {
    static let assets: [Asset] = [
        makeStock(
            name: "Apple",
            symbol: "AAPL",
            price: 227.48,
            image: "apple.logo",
            trend: .up,
            volatility: 0.012
        ),
        makeStock(
            name: "Tesla",
            symbol: "TSLA",
            price: 248.91,
            image: "bolt.car.fill",
            trend: .volatile,
            volatility: 0.028
        ),
        makeCollectible(
            name: "Charizard ex",
            symbol: "PKMN-SV3-223",
            price: 312.50,
            image: "flame.fill",
            trend: .up,
            volatility: 0.045
        ),
        makeCollectible(
            name: "Black Lotus",
            symbol: "MTG-LEA-232",
            price: 18_400,
            image: "leaf.fill",
            trend: .down,
            volatility: 0.018
        )
    ]

    private enum Trend {
        case up, down, volatile
    }

    private static func makeStock(
        name: String,
        symbol: String,
        price: Double,
        image: String,
        trend: Trend,
        volatility: Double
    ) -> Asset {
        Asset(
            name: name,
            symbol: symbol,
            category: .stock,
            currentPrice: price,
            history: history(endingAt: price, trend: trend, volatility: volatility),
            alertThresholdPercent: symbol == "TSLA" ? 10 : 5,
            systemImage: image
        )
    }

    private static func makeCollectible(
        name: String,
        symbol: String,
        price: Double,
        image: String,
        trend: Trend,
        volatility: Double
    ) -> Asset {
        Asset(
            name: name,
            symbol: symbol,
            category: .collectible,
            currentPrice: price,
            history: history(endingAt: price, trend: trend, volatility: volatility),
            alertThresholdPercent: 10,
            systemImage: image
        )
    }

    private static func history(endingAt last: Double, trend: Trend, volatility: Double) -> [PricePoint] {
        let count = 36
        var prices: [Double] = [last]
        var value = last

        for index in 1..<count {
            let drift: Double
            switch trend {
            case .up: drift = 0.004
            case .down: drift = -0.003
            case .volatile: drift = (index % 5 == 0) ? 0.02 : -0.008
            }
            let noise = Double.random(in: -volatility...volatility)
            value = max(0.01, value / (1 + drift + noise))
            prices.insert(value, at: 0)
        }

        let start = Date().addingTimeInterval(-Double(count - 1) * 15 * 60)
        return prices.enumerated().map { index, price in
            PricePoint(date: start.addingTimeInterval(Double(index) * 15 * 60), price: price)
        }
    }
}
