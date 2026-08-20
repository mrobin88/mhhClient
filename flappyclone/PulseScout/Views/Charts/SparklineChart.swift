import Charts
import SwiftUI

struct SparklineChart: View {
    let points: [PricePoint]
    var lineColor: Color = Theme.gain

    private var sorted: [PricePoint] {
        points.sorted { $0.date < $1.date }
    }

    var body: some View {
        Chart(sorted) { point in
            AreaMark(
                x: .value("Time", point.date),
                y: .value("Price", point.price)
            )
            .interpolationMethod(.catmullRom)
            .foregroundStyle(
                LinearGradient(
                    colors: [lineColor.opacity(0.28), lineColor.opacity(0.0)],
                    startPoint: .top,
                    endPoint: .bottom
                )
            )

            LineMark(
                x: .value("Time", point.date),
                y: .value("Price", point.price)
            )
            .interpolationMethod(.catmullRom)
            .foregroundStyle(lineColor)
            .lineStyle(StrokeStyle(lineWidth: 2, lineCap: .round, lineJoin: .round))
        }
        .chartXAxis(.hidden)
        .chartYAxis(.hidden)
        .chartLegend(.hidden)
        .chartYScale(domain: yDomain)
        .accessibilityLabel("Price trend")
    }

    private var yDomain: ClosedRange<Double> {
        let prices = sorted.map(\.price)
        guard let min = prices.min(), let max = prices.max(), min != max else {
            let value = prices.first ?? 0
            return (value * 0.98)...(value * 1.02 + 0.01)
        }
        let pad = (max - min) * 0.12
        return (min - pad)...(max + pad)
    }
}

#Preview {
    SparklineChart(points: MockData.assets[0].history)
        .frame(height: 56)
        .padding()
        .background(Theme.background)
}
