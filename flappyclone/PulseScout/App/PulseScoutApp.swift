import SwiftUI

@main
struct PulseScoutApp: App {
    @State private var dashboard = DashboardViewModel()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environment(dashboard)
                .preferredColorScheme(.dark)
        }
    }
}
