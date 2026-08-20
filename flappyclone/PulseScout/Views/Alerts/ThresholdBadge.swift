import SwiftUI

struct ThresholdBadge: View {
    let isActive: Bool
    let percentChange: Double

    @State private var pulse = false

    var body: some View {
        if isActive {
            HStack(spacing: 4) {
                Image(systemName: percentChange >= 0 ? "arrow.up.right" : "arrow.down.right")
                    .font(.system(size: 10, weight: .bold))
                Text("ALERT")
                    .font(.system(size: 9, weight: .heavy, design: .rounded))
                    .tracking(0.6)
            }
            .foregroundStyle(Theme.background)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(percentChange >= 0 ? Theme.gain : Theme.loss)
            .clipShape(Capsule())
            .shadow(color: (percentChange >= 0 ? Theme.gain : Theme.loss).opacity(0.55), radius: pulse ? 10 : 4)
            .opacity(pulse ? 0.55 : 1)
            .onAppear {
                withAnimation(.easeInOut(duration: 0.7).repeatForever(autoreverses: true)) {
                    pulse = true
                }
            }
            .accessibilityLabel("Custom threshold breached")
        }
    }
}

#Preview {
    VStack {
        ThresholdBadge(isActive: true, percentChange: 12)
        ThresholdBadge(isActive: true, percentChange: -8)
    }
    .padding()
    .background(Theme.background)
}
