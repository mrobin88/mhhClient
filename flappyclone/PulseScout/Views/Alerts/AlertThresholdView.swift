import SwiftUI

struct AlertThresholdView: View {
    @Environment(DashboardViewModel.self) private var dashboard
    @Environment(\.dismiss) private var dismiss

    let title: String
    let assetID: UUID?

    @State private var model: AlertSettingsViewModel

    init(title: String, initialThreshold: Double, allowApplyToAll: Bool, assetID: UUID?) {
        self.title = title
        self.assetID = assetID
        _model = State(
            initialValue: AlertSettingsViewModel(
                initialThreshold: initialThreshold,
                applyToAll: allowApplyToAll && assetID == nil
            )
        )
    }

    var body: some View {
        @Bindable var model = model

        NavigationStack {
            ZStack {
                Theme.background.ignoresSafeArea()

                VStack(alignment: .leading, spacing: 24) {
                    Text("Fires when the last two price points move by at least this amount.")
                        .font(.system(size: 14, weight: .medium, design: .rounded))
                        .foregroundStyle(Theme.textSecondary)

                    VStack(spacing: 8) {
                        Text(model.formattedThreshold)
                            .font(.system(size: 56, weight: .bold, design: .rounded))
                            .foregroundStyle(Theme.gold)
                            .frame(maxWidth: .infinity)
                        Text("jump threshold")
                            .font(.system(size: 12, weight: .semibold, design: .rounded))
                            .foregroundStyle(Theme.textMuted)
                    }
                    .padding(.vertical, 8)

                    Slider(
                        value: $model.threshold,
                        in: model.range,
                        step: 1
                    )
                    .tint(Theme.gold)
                    .accessibilityLabel("Alert threshold percent")

                    HStack(spacing: 10) {
                        ForEach(model.presets, id: \.self) { preset in
                            Button {
                                model.selectPreset(preset)
                            } label: {
                                Text("\(Int(preset))%")
                                    .font(.system(size: 13, weight: .bold, design: .rounded))
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 10)
                                    .foregroundStyle(model.threshold == preset ? Theme.background : Theme.textPrimary)
                                    .background(model.threshold == preset ? Theme.gold : Theme.cardElevated)
                                    .clipShape(Capsule())
                            }
                            .buttonStyle(.plain)
                        }
                    }

                    Toggle(isOn: $model.applyToAll) {
                        Text("Apply to every watched asset")
                            .font(.system(size: 14, weight: .medium, design: .rounded))
                    }
                    .tint(Theme.accent)
                    .foregroundStyle(Theme.textPrimary)

                    Spacer()

                    Button {
                        model.commit(to: dashboard, assetID: assetID)
                        dismiss()
                    } label: {
                        Text("Save Threshold")
                            .font(.system(size: 16, weight: .bold, design: .rounded))
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 14)
                            .foregroundStyle(Theme.background)
                            .background(Theme.gold)
                            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                    }
                    .buttonStyle(.plain)
                }
                .padding(24)
            }
            .navigationTitle(title)
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
}

#Preview {
    AlertThresholdView(
        title: "Set Alert Threshold",
        initialThreshold: 10,
        allowApplyToAll: true,
        assetID: nil
    )
    .environment(DashboardViewModel.preview)
}
