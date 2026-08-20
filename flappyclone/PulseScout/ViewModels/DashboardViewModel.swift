import Foundation
import Observation

@MainActor
@Observable
final class DashboardViewModel {
    var assets: [Asset]
    var selectedCategory: AssetCategory?
    var recentAlerts: [PriceAlert]
    var notificationsAllowed = false
    var isLive = false

    let subscription: SubscriptionService

    private let notifications: NotificationServicing
    private let monitor: PriceMonitorService
    private var lastEvaluatedJump: [UUID: Double] = [:]
    private var monitorStarted = false

    init(
        assets: [Asset] = MockData.assets,
        subscription: SubscriptionService = SubscriptionService(),
        notifications: NotificationServicing = NotificationService(),
        monitor: PriceMonitorService = PriceMonitorService()
    ) {
        self.assets = assets
        self.subscription = subscription
        self.notifications = notifications
        self.monitor = monitor
        self.recentAlerts = []
    }

    var visibleAssets: [Asset] {
        guard let selectedCategory else { return assets }
        return assets.filter { $0.category == selectedCategory }
    }

    var breachedAssetIDs: Set<UUID> {
        Set(assets.filter(isBreached).map(\.id))
    }

    func start() async {
        notificationsAllowed = await notifications.requestAuthorization()
        await subscription.refresh()
        startLiveQuotes()
    }

    func startLiveQuotes() {
        guard !monitorStarted else { return }
        monitorStarted = true
        isLive = true
        monitor.onTick = { [weak self] in
            Task { @MainActor in
                self?.advanceQuotes()
            }
        }
        monitor.start()
    }

    func isBreached(_ asset: Asset) -> Bool {
        guard let jump = PriceJumpEngine.latestJump(for: asset) else { return false }
        return PriceJumpEngine.exceedsThreshold(jump, threshold: asset.alertThresholdPercent)
    }

    func latestJump(for asset: Asset) -> Double {
        PriceJumpEngine.latestJump(for: asset) ?? 0
    }

    func updateThreshold(_ threshold: Double, for assetID: UUID) {
        guard let index = assets.firstIndex(where: { $0.id == assetID }) else { return }
        assets[index].alertThresholdPercent = threshold
    }

    func applyThresholdToAll(_ threshold: Double) {
        for index in assets.indices {
            assets[index].alertThresholdPercent = threshold
        }
    }

    func advanceQuotes() {
        for index in assets.indices {
            let next = monitor.nextPrice(for: assets[index])
            assets[index].appendPrice(next)
            evaluateAlert(for: assets[index])
        }
    }

    private func evaluateAlert(for asset: Asset) {
        guard let jump = PriceJumpEngine.latestJump(for: asset),
              PriceJumpEngine.exceedsThreshold(jump, threshold: asset.alertThresholdPercent) else {
            return
        }

        if lastEvaluatedJump[asset.id] == jump { return }
        lastEvaluatedJump[asset.id] = jump

        let delay = subscription.tier.alertDelay
        var alert = PriceAlert(
            assetID: asset.id,
            assetName: asset.name,
            percentChange: jump,
            isDelayed: delay > 0
        )
        if delay == 0 {
            alert.deliveredAt = .now
        }

        recentAlerts.insert(alert, at: 0)
        if recentAlerts.count > 20 {
            recentAlerts = Array(recentAlerts.prefix(20))
        }

        Task {
            await notifications.deliver(alert, delay: delay)
        }
    }
}

extension DashboardViewModel {
    static var preview: DashboardViewModel {
        DashboardViewModel()
    }
}
