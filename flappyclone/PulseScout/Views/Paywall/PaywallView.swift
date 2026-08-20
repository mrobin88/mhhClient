import SwiftUI

struct PaywallView: View {
    @Environment(DashboardViewModel.self) private var dashboard
    @Environment(\.dismiss) private var dismiss
    @State private var isPurchasing = false

    var body: some View {
        NavigationStack {
            ZStack {
                Theme.background.ignoresSafeArea()

                ScrollView {
                    VStack(alignment: .leading, spacing: 24) {
                        VStack(alignment: .leading, spacing: 10) {
                            Text("INSTANT SCOUT")
                                .font(.system(size: 12, weight: .heavy, design: .rounded))
                                .tracking(2)
                                .foregroundStyle(Theme.gold)
                            Text("Beat the shop. Beat the tape.")
                                .font(.system(size: 28, weight: .bold, design: .rounded))
                                .foregroundStyle(Theme.textPrimary)
                            Text("Free alerts wait 2–4 hours. Instant Scout fires the second a card or stock clears your threshold.")
                                .font(.system(size: 14, weight: .medium, design: .rounded))
                                .foregroundStyle(Theme.textSecondary)
                        }

                        VStack(spacing: 12) {
                            tierRow(
                                title: "Free",
                                price: "$0",
                                detail: "Price alerts delayed 2–4 hours",
                                highlighted: dashboard.subscription.tier == .free
                            )
                            tierRow(
                                title: "Instant Scout",
                                price: "$4.99/mo",
                                detail: "Real-time local notifications",
                                highlighted: dashboard.subscription.tier == .instantScout
                            )
                        }

                        if dashboard.subscription.tier == .instantScout {
                            Button("Back to Free (demo)") {
                                dashboard.subscription.restoreFree()
                                dismiss()
                            }
                            .font(.system(size: 13, weight: .semibold, design: .rounded))
                            .foregroundStyle(Theme.textMuted)
                            .frame(maxWidth: .infinity)
                        } else {
                            Button {
                                Task {
                                    isPurchasing = true
                                    await dashboard.subscription.unlockInstantScout()
                                    isPurchasing = false
                                    dismiss()
                                }
                            } label: {
                                HStack {
                                    if isPurchasing {
                                        ProgressView()
                                            .tint(Theme.background)
                                    }
                                    Text("Unlock Instant Scout — $4.99/mo")
                                        .font(.system(size: 15, weight: .bold, design: .rounded))
                                }
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 16)
                                .foregroundStyle(Theme.background)
                                .background(Theme.gold)
                                .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                            }
                            .buttonStyle(.plain)
                            .disabled(isPurchasing)
                        }

                        Text("Demo storefront only. Replace SubscriptionService with RevenueCat Purchases.shared before shipping.")
                            .font(.system(size: 11, weight: .medium, design: .rounded))
                            .foregroundStyle(Theme.textMuted)
                    }
                    .padding(24)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                        .foregroundStyle(Theme.textSecondary)
                }
            }
        }
        .preferredColorScheme(.dark)
    }

    private func tierRow(title: String, price: String, detail: String, highlighted: Bool) -> some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 16, weight: .bold, design: .rounded))
                    .foregroundStyle(Theme.textPrimary)
                Text(detail)
                    .font(.system(size: 12, weight: .medium, design: .rounded))
                    .foregroundStyle(Theme.textSecondary)
            }
            Spacer()
            Text(price)
                .font(.system(size: 15, weight: .bold, design: .rounded))
                .foregroundStyle(highlighted ? Theme.gold : Theme.textPrimary)
        }
        .padding(16)
        .background(Theme.card)
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(highlighted ? Theme.gold.opacity(0.7) : Theme.border, lineWidth: highlighted ? 1.5 : 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

#Preview {
    PaywallView()
        .environment(DashboardViewModel.preview)
}
