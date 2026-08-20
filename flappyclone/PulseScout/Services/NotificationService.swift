import Foundation
import UserNotifications

protocol NotificationServicing {
    func requestAuthorization() async -> Bool
    func deliver(_ alert: PriceAlert, delay: TimeInterval) async
}

final class NotificationService: NotificationServicing {
    private let center: UNUserNotificationCenter

    init(center: UNUserNotificationCenter = .current()) {
        self.center = center
    }

    func requestAuthorization() async -> Bool {
        do {
            return try await center.requestAuthorization(options: [.alert, .sound, .badge])
        } catch {
            return false
        }
    }

    func deliver(_ alert: PriceAlert, delay: TimeInterval) async {
        let content = UNMutableNotificationContent()
        content.title = alert.isSpike ? "🚨 Price Jump!" : "📉 Price Drop!"
        let amount = String(format: "%.1f", abs(alert.percentChange))
        if alert.isSpike {
            content.body = "\(alert.assetName) has spiked by \(amount)%!"
        } else {
            content.body = "\(alert.assetName) has fallen by \(amount)%!"
        }
        content.sound = .default
        content.userInfo = [
            "assetID": alert.assetID.uuidString,
            "percentChange": alert.percentChange
        ]

        let interval = max(0.5, delay)
        let trigger = UNTimeIntervalNotificationTrigger(timeInterval: interval, repeats: false)
        let request = UNNotificationRequest(
            identifier: alert.id.uuidString,
            content: content,
            trigger: trigger
        )

        try? await center.add(request)
    }
}
