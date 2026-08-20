import SwiftUI

struct ContentView: View {
    @Environment(DashboardViewModel.self) private var dashboard

    var body: some View {
        DashboardView()
            .task {
                await dashboard.start()
            }
    }
}

#Preview {
    ContentView()
        .environment(DashboardViewModel.preview)
        .preferredColorScheme(.dark)
}
