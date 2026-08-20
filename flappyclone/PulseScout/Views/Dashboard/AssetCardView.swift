import SwiftUI

struct AssetCardView: View {
    let asset: Asset
    let jump: Double
    let isBreached: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top) {
                icon
                VStack(alignment: .leading, spacing: 4) {
                    Text(asset.symbol)
                        .font(.system(size: 13, weight: .bold, design: .rounded))
                        .foregroundStyle(Theme.textSecondary)
                    Text(asset.name)
                        .font(.system(size: 18, weight: .semibold, design: .rounded))
                        .foregroundStyle(Theme.textPrimary)
                }
                Spacer()
                categoryChip
            }

            HStack(alignment: .bottom, spacing: 12) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(asset.currentPrice.formatted(.currency(code: asset.currencyCode)))
                        .font(.system(size: 22, weight: .bold, design: .rounded))
                        .foregroundStyle(Theme.textPrimary)
                        .minimumScaleFactor(0.7)
                        .lineLimit(1)

                    HStack(spacing: 8) {
                        changeLabel
                        ThresholdBadge(isActive: isBreached, percentChange: jump)
                    }
                }

                SparklineChart(points: asset.history, lineColor: Theme.trendColor(asset.sessionChangePercent))
                    .frame(height: 52)
            }

            HStack {
                Label(
                    "Alert at \(Int(asset.alertThresholdPercent))%",
                    systemImage: "bell.fill"
                )
                .font(.system(size: 11, weight: .medium, design: .rounded))
                .foregroundStyle(Theme.textMuted)
                Spacer()
                Text(asset.sessionChangePercent, format: .number.precision(.fractionLength(1)).sign(strategy: .always()))
                    .font(.system(size: 11, weight: .semibold, design: .rounded))
                    .foregroundStyle(Theme.trendColor(asset.sessionChangePercent))
                + Text("% session")
                    .font(.system(size: 11, weight: .medium, design: .rounded))
                    .foregroundStyle(Theme.textMuted)
            }
        }
        .padding(16)
        .background(Theme.card)
        .overlay(
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .stroke(
                    isBreached
                        ? Theme.trendColor(jump).opacity(0.55)
                        : Theme.border,
                    lineWidth: isBreached ? 1.4 : 1
                )
        )
        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private var icon: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(Theme.color(for: asset.category).opacity(0.16))
                .frame(width: 42, height: 42)
            Image(systemName: asset.systemImage)
                .font(.system(size: 18, weight: .semibold))
                .foregroundStyle(Theme.color(for: asset.category))
        }
    }

    private var categoryChip: some View {
        Text(asset.category.singular.uppercased())
            .font(.system(size: 9, weight: .heavy, design: .rounded))
            .tracking(0.8)
            .foregroundStyle(Theme.color(for: asset.category))
            .padding(.horizontal, 8)
            .padding(.vertical, 5)
            .background(Theme.color(for: asset.category).opacity(0.14))
            .clipShape(Capsule())
    }

    private var changeLabel: some View {
        Text(jump, format: .number.precision(.fractionLength(1)).sign(strategy: .always()))
            .font(.system(size: 13, weight: .bold, design: .rounded))
            .foregroundStyle(Theme.trendColor(jump))
        + Text("%")
            .font(.system(size: 13, weight: .bold, design: .rounded))
            .foregroundStyle(Theme.trendColor(jump))
    }
}

#Preview {
    AssetCardView(asset: MockData.assets[0], jump: 6.2, isBreached: true)
        .padding()
        .background(Theme.background)
}
