import SwiftUI

struct AssetDetailView: View {
    @Environment(DashboardViewModel.self) private var dashboard
    let assetID: UUID

    @State private var showThreshold = false

    private var asset: Asset? {
        dashboard.assets.first { $0.id == assetID }
    }

    var body: some View {
        ZStack {
            Theme.background.ignoresSafeArea()

            if let asset {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        header(asset)
                        chartCard(asset)
                        stats(asset)
                        recentMoves
                    }
                    .padding(20)
                }
            } else {
                Text("Asset unavailable")
                    .foregroundStyle(Theme.textSecondary)
            }
        }
        .navigationTitle(asset?.symbol ?? "Asset")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    showThreshold = true
                } label: {
                    Image(systemName: "bell.badge")
                        .foregroundStyle(Theme.gold)
                }
                .accessibilityLabel("Set alert threshold")
            }
        }
        .sheet(isPresented: $showThreshold) {
            if let asset {
                AlertThresholdView(
                    title: "Set Alert Threshold",
                    initialThreshold: asset.alertThresholdPercent,
                    allowApplyToAll: true,
                    assetID: asset.id
                )
                .presentationDetents([.medium, .large])
            }
        }
    }

    private func header(_ asset: Asset) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(asset.name)
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                    .foregroundStyle(Theme.textPrimary)
                Spacer()
                ThresholdBadge(
                    isActive: dashboard.isBreached(asset),
                    percentChange: dashboard.latestJump(for: asset)
                )
            }
            Text(asset.currentPrice.formatted(.currency(code: asset.currencyCode)))
                .font(.system(size: 36, weight: .bold, design: .rounded))
                .foregroundStyle(Theme.textPrimary)

            let jump = dashboard.latestJump(for: asset)
            Text("Last tick \(jump, format: .number.precision(.fractionLength(2)).sign(strategy: .always()))%")
                .font(.system(size: 14, weight: .semibold, design: .rounded))
                .foregroundStyle(Theme.trendColor(jump))
        }
    }

    private func chartCard(_ asset: Asset) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("RECENT TREND")
                .font(.system(size: 11, weight: .heavy, design: .rounded))
                .tracking(1.2)
                .foregroundStyle(Theme.textMuted)
            SparklineChart(
                points: asset.history,
                lineColor: Theme.trendColor(asset.sessionChangePercent)
            )
            .frame(height: 180)
        }
        .padding(16)
        .background(Theme.card)
        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .stroke(Theme.border, lineWidth: 1)
        )
    }

    private func stats(_ asset: Asset) -> some View {
        HStack(spacing: 12) {
            stat("Category", asset.category.singular)
            stat("Threshold", "\(Int(asset.alertThresholdPercent))%")
            stat("Session", String(format: "%+.1f%%", asset.sessionChangePercent))
        }
    }

    private func stat(_ title: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .heavy, design: .rounded))
                .foregroundStyle(Theme.textMuted)
            Text(value)
                .font(.system(size: 15, weight: .semibold, design: .rounded))
                .foregroundStyle(Theme.textPrimary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Theme.card)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }

    private var recentMoves: some View {
        let related = dashboard.recentAlerts.filter { $0.assetID == assetID }
        return VStack(alignment: .leading, spacing: 12) {
            Text("ALERT LOG")
                .font(.system(size: 11, weight: .heavy, design: .rounded))
                .tracking(1.2)
                .foregroundStyle(Theme.textMuted)

            if related.isEmpty {
                Text("No threshold breaches yet. Live quotes will trip this when a jump clears your setting.")
                    .font(.system(size: 13, weight: .medium, design: .rounded))
                    .foregroundStyle(Theme.textSecondary)
            } else {
                ForEach(related.prefix(8)) { alert in
                    HStack {
                        Text(alert.isSpike ? "▲" : "▼")
                            .foregroundStyle(alert.isSpike ? Theme.gain : Theme.loss)
                        Text(String(format: "%+.1f%%", alert.percentChange))
                            .font(.system(size: 14, weight: .bold, design: .rounded))
                            .foregroundStyle(Theme.textPrimary)
                        Spacer()
                        if alert.isDelayed {
                            Text("Delayed")
                                .font(.system(size: 11, weight: .semibold, design: .rounded))
                                .foregroundStyle(Theme.accent)
                        }
                        Text(alert.triggeredAt, style: .time)
                            .font(.system(size: 12, weight: .medium, design: .rounded))
                            .foregroundStyle(Theme.textMuted)
                    }
                    .padding(.vertical, 6)
                }
            }
        }
        .padding(16)
        .background(Theme.card)
        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
    }
}
