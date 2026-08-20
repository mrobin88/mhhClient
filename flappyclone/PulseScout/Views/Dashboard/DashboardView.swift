import SwiftUI

struct DashboardView: View {
    @Environment(DashboardViewModel.self) private var dashboard
    @State private var showGlobalAlerts = false
    @State private var showPaywall = false

    var body: some View {
        @Bindable var dashboard = dashboard

        NavigationStack {
            ZStack {
                Theme.background.ignoresSafeArea()

                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        header
                        filterRow
                        liveBanner
                        assetList
                    }
                    .padding(.horizontal, 20)
                    .padding(.bottom, 32)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button {
                        showGlobalAlerts = true
                    } label: {
                        Image(systemName: "slider.horizontal.3")
                            .foregroundStyle(Theme.textPrimary)
                    }
                    .accessibilityLabel("Set alert threshold")
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        showPaywall = true
                    } label: {
                        Image(systemName: dashboard.subscription.tier == .instantScout ? "bolt.fill" : "bolt.badge.automatic")
                            .foregroundStyle(dashboard.subscription.tier == .instantScout ? Theme.gold : Theme.accent)
                    }
                    .accessibilityLabel("Subscription")
                }
            }
            .navigationDestination(for: UUID.self) { id in
                AssetDetailView(assetID: id)
            }
            .sheet(isPresented: $showGlobalAlerts) {
                AlertThresholdView(
                    title: "Default Alert Threshold",
                    initialThreshold: dashboard.assets.first?.alertThresholdPercent ?? 5,
                    allowApplyToAll: true,
                    assetID: nil
                )
                .presentationDetents([.medium, .large])
            }
            .sheet(isPresented: $showPaywall) {
                PaywallView()
            }
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Text("PULSESCOUT")
                    .font(.system(size: 11, weight: .heavy, design: .rounded))
                    .tracking(2.4)
                    .foregroundStyle(Theme.gold)
                if dashboard.isLive {
                    Circle()
                        .fill(Theme.gain)
                        .frame(width: 7, height: 7)
                        .shadow(color: Theme.gain, radius: 4)
                }
            }
            Text("Alert Dashboard")
                .font(.system(size: 32, weight: .bold, design: .rounded))
                .foregroundStyle(Theme.textPrimary)
            Text("Watch stocks and collectibles. Get notified when a move clears your threshold.")
                .font(.system(size: 14, weight: .medium, design: .rounded))
                .foregroundStyle(Theme.textSecondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .padding(.top, 8)
    }

    private var filterRow: some View {
        HStack(spacing: 8) {
            chip(title: "All", selected: dashboard.selectedCategory == nil) {
                dashboard.selectedCategory = nil
            }
            ForEach(AssetCategory.allCases) { category in
                chip(title: category.title, selected: dashboard.selectedCategory == category) {
                    dashboard.selectedCategory = category
                }
            }
            Spacer()
        }
    }

    private func chip(title: String, selected: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 12, weight: .semibold, design: .rounded))
                .foregroundStyle(selected ? Theme.background : Theme.textSecondary)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(selected ? Theme.gold : Theme.cardElevated)
                .clipShape(Capsule())
        }
        .buttonStyle(.plain)
    }

    private var liveBanner: some View {
        HStack(spacing: 10) {
            Image(systemName: dashboard.subscription.tier == .instantScout ? "bolt.fill" : "clock.fill")
                .foregroundStyle(dashboard.subscription.tier == .instantScout ? Theme.gold : Theme.accent)
            VStack(alignment: .leading, spacing: 2) {
                Text(dashboard.subscription.tier.displayName)
                    .font(.system(size: 13, weight: .bold, design: .rounded))
                    .foregroundStyle(Theme.textPrimary)
                Text(dashboard.subscription.tier.delayCopy)
                    .font(.system(size: 11, weight: .medium, design: .rounded))
                    .foregroundStyle(Theme.textSecondary)
            }
            Spacer()
            Text("\(dashboard.breachedAssetIDs.count) hot")
                .font(.system(size: 11, weight: .bold, design: .rounded))
                .foregroundStyle(Theme.gain)
        }
        .padding(14)
        .background(Theme.card)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Theme.border, lineWidth: 1)
        )
    }

    private var assetList: some View {
        LazyVStack(spacing: 14) {
            ForEach(dashboard.visibleAssets) { asset in
                NavigationLink(value: asset.id) {
                    AssetCardView(
                        asset: asset,
                        jump: dashboard.latestJump(for: asset),
                        isBreached: dashboard.isBreached(asset)
                    )
                }
                .buttonStyle(.plain)
            }
        }
    }
}

#Preview {
    DashboardView()
        .environment(DashboardViewModel.preview)
}
