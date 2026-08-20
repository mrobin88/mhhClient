import Foundation

/// Simulates live quotes so the dashboard and alert engine can be tested without a market API.
final class PriceMonitorService {
    var onTick: (() -> Void)?

    private var timer: Timer?
    private let interval: TimeInterval

    init(interval: TimeInterval = 4) {
        self.interval = interval
    }

    func start() {
        stop()
        let timer = Timer.scheduledTimer(withTimeInterval: interval, repeats: true) { [weak self] _ in
            self?.onTick?()
        }
        timer.tolerance = 0.3
        RunLoop.main.add(timer, forMode: .common)
        self.timer = timer
    }

    func stop() {
        timer?.invalidate()
        timer = nil
    }

    /// Random walk. Collectibles move harder; occasional spikes exercise the alert engine.
    func nextPrice(for asset: Asset) -> Double {
        let base = asset.category == .collectible ? 0.035 : 0.016
        let spikeChance = asset.category == .collectible ? 0.14 : 0.09
        let spiked = Double.random(in: 0...1) < spikeChance
        let magnitude = spiked ? Double.random(in: 0.06...0.18) : Double.random(in: 0...base)
        let direction: Double = Bool.random() ? 1 : -1
        let move = (spiked ? 1 : direction) * magnitude
        return max(0.01, asset.currentPrice * (1 + move))
    }

    deinit {
        stop()
    }
}
