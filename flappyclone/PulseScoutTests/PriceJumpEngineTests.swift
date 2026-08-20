import XCTest
@testable import PulseScout

final class PriceJumpEngineTests: XCTestCase {
    func testPercentChangeIncrease() {
        let change = PriceJumpEngine.percentChange(from: 100, to: 110)
        XCTAssertEqual(change, 10, accuracy: 0.0001)
    }

    func testPercentChangeDrop() {
        let change = PriceJumpEngine.percentChange(from: 200, to: 150)
        XCTAssertEqual(change, -25, accuracy: 0.0001)
    }

    func testZeroPreviousPriceIsSafe() {
        XCTAssertEqual(PriceJumpEngine.percentChange(from: 0, to: 10), 0)
    }

    func testLatestJumpUsesLastTwoPoints() {
        let history = [
            PricePoint(date: Date().addingTimeInterval(-120), price: 100),
            PricePoint(date: Date().addingTimeInterval(-60), price: 108),
            PricePoint(date: Date(), price: 135)
        ]
        let jump = PriceJumpEngine.latestJump(in: history)
        XCTAssertEqual(jump ?? 0, 25, accuracy: 0.0001)
    }

    func testThresholdBreachOnSpike() {
        XCTAssertTrue(PriceJumpEngine.exceedsThreshold(12, threshold: 10))
        XCTAssertFalse(PriceJumpEngine.exceedsThreshold(9.9, threshold: 10))
        XCTAssertTrue(PriceJumpEngine.exceedsThreshold(-11, threshold: 10))
    }

    func testEvaluateBuildsSpikeAlert() {
        var asset = MockData.assets[0]
        asset.alertThresholdPercent = 5
        asset.history = [
            PricePoint(date: Date().addingTimeInterval(-60), price: 100),
            PricePoint(date: Date(), price: 108)
        ]
        asset.currentPrice = 108

        let alert = PriceJumpEngine.evaluate(asset: asset)
        XCTAssertNotNil(alert)
        XCTAssertEqual(alert?.assetName, asset.name)
        XCTAssertEqual(alert?.percentChange ?? 0, 8, accuracy: 0.0001)
        XCTAssertTrue(alert?.isSpike ?? false)
    }
}
