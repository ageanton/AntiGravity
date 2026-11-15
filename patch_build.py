#!/usr/bin/env python3
import sys

def patch_motif():
    with open("motif_build_v12.txt", "r", encoding="utf-8") as f:
        text = f.read()

    if "hasReceivedExplicitThinkingChannel" in text and "parser.transitionToPostThinkingAnswer()" in text:
        print("motif_build_v12.txt is already patched.")
        return

    old_start = "// MARK: - Stop-Safe Stateful Thinking Stream Parser\npublic final class StatefulThinkingStreamParser {"
    old_end = """    private func trailingPartialTagIndex(in text: String, tags: [String]) -> String.Index? {
        guard let lastAngle = text.lastIndex(of: "<") else { return nil }
        let suffix = String(text[lastAngle...])
        for tag in tags {
            if tag.hasPrefix(suffix) && suffix.count < tag.count {
                return lastAngle
            }
        }
        return nil
    }
}"""

    new_parser = r"""// MARK: - Stop-Safe Stateful Thinking Stream Parser
public final class StatefulThinkingStreamParser {
    public enum State {
        case normalOrAwaitingOpeningTag
        case insideThinkingBlock
        case postThinkingAnswer
    }

    public private(set) var state: State = .normalOrAwaitingOpeningTag
    private var pendingBuffer: String = ""
    private var hasReceivedExplicitThinkingChannel: Bool = false
    private let openTags = [
        "<think>", "<thought>", "<reasoning>", "<|thought|>",
        "<|begin_of_thought|>", "<|start_of_thought|>",
        "<｜begin of thinking｜>"
    ]
    private let closeTags = [
        "</think>", "</thought>", "</reasoning>", "<|/thought|>",
        "<|end_of_thought|>", "<|endofthought|>", "<end_of_thought>",
        "<｜end of thinking｜>", "</details>"
    ]

    public private(set) var accumulatedThinking: String = ""
    public private(set) var accumulatedAnswer: String = ""
    public private(set) var isCurrentlyThinking: Bool = false
    public private(set) var thinkingStartTime: Date?
    public private(set) var thinkingDurationSeconds: Double = 0.0

    public init() {}

    public func preloadExisting(
        thinking: String,
        answer: String,
        resumeInsideThinking: Bool,
        priorThinkingDuration: Double = 0.0
    ) {
        accumulatedThinking = thinking
        accumulatedAnswer = answer
        thinkingDurationSeconds = priorThinkingDuration
        if resumeInsideThinking {
            state = .insideThinkingBlock
            isCurrentlyThinking = true
            thinkingStartTime = Date().addingTimeInterval(-priorThinkingDuration)
        } else if !thinking.isEmpty || !answer.isEmpty {
            state = .postThinkingAnswer
            isCurrentlyThinking = false
        } else {
            state = .normalOrAwaitingOpeningTag
            isCurrentlyThinking = false
        }
    }

    public func ingestExplicitThinkingDelta(_ delta: String) {
        guard !delta.isEmpty else { return }
        hasReceivedExplicitThinkingChannel = true
        state = .insideThinkingBlock
        if thinkingStartTime == nil {
            thinkingStartTime = Date()
        }
        isCurrentlyThinking = true
        accumulatedThinking += delta
        if let start = thinkingStartTime {
            thinkingDurationSeconds = Date().timeIntervalSince(start)
        }
    }

    public func ingestContentChunk(_ chunk: String) {
        guard !chunk.isEmpty else { return }
        if hasReceivedExplicitThinkingChannel && state == .insideThinkingBlock {
            transitionToPostThinkingAnswer()
        }
        pendingBuffer += chunk
        processBuffer()
    }

    public func transitionToPostThinkingAnswer() {
        if !pendingBuffer.isEmpty {
            if state == .insideThinkingBlock {
                accumulatedThinking += pendingBuffer
            } else {
                accumulatedAnswer += pendingBuffer
            }
            pendingBuffer = ""
        }
        state = .postThinkingAnswer
        isCurrentlyThinking = false
        if let start = thinkingStartTime, thinkingDurationSeconds == 0 {
            thinkingDurationSeconds = Date().timeIntervalSince(start)
        }
    }

    public func flushPendingBufferWithoutLosingState(markComplete: Bool) {
        if !pendingBuffer.isEmpty {
            switch state {
            case .insideThinkingBlock:
                accumulatedThinking += pendingBuffer
            case .normalOrAwaitingOpeningTag, .postThinkingAnswer:
                accumulatedAnswer += pendingBuffer
            }
            pendingBuffer = ""
        }
        if let start = thinkingStartTime, isCurrentlyThinking {
            thinkingDurationSeconds = Date().timeIntervalSince(start)
        }
        if markComplete {
            isCurrentlyThinking = false
        }
    }

    private func processBuffer() {
        var keepProcessing = true
        while keepProcessing && !pendingBuffer.isEmpty {
            keepProcessing = false

            switch state {
            case .normalOrAwaitingOpeningTag:
                if let match = findFirstTag(in: pendingBuffer, tags: openTags) {
                    let prefix = String(pendingBuffer[..<match.range.lowerBound])
                    if !prefix.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        accumulatedAnswer += prefix
                    }
                    pendingBuffer.removeSubrange(..<match.range.upperBound)
                    state = .insideThinkingBlock
                    isCurrentlyThinking = true
                    if thinkingStartTime == nil {
                        thinkingStartTime = Date()
                    }
                    keepProcessing = true
                } else if let closeMatch = findFirstTag(in: pendingBuffer, tags: closeTags) {
                    let thoughtSegment = String(pendingBuffer[..<closeMatch.range.lowerBound])
                    accumulatedThinking += accumulatedAnswer + thoughtSegment
                    accumulatedAnswer = ""
                    pendingBuffer.removeSubrange(..<closeMatch.range.upperBound)
                    if let first = pendingBuffer.first, first.isNewline {
                        pendingBuffer.removeFirst()
                    }
                    state = .postThinkingAnswer
                    isCurrentlyThinking = false
                    keepProcessing = true
                } else if let partialIdx = trailingPartialTagIndex(in: pendingBuffer, tags: openTags + closeTags) {
                    let safePrefix = String(pendingBuffer[..<partialIdx])
                    accumulatedAnswer += safePrefix
                    pendingBuffer.removeSubrange(..<partialIdx)
                } else {
                    if isCurrentlyThinking && !accumulatedThinking.isEmpty {
                        if let start = thinkingStartTime {
                            thinkingDurationSeconds = Date().timeIntervalSince(start)
                        }
                        isCurrentlyThinking = false
                    }
                    accumulatedAnswer += pendingBuffer
                    pendingBuffer = ""
                }

            case .insideThinkingBlock:
                if let start = thinkingStartTime {
                    thinkingDurationSeconds = Date().timeIntervalSince(start)
                }
                if let match = findFirstTag(in: pendingBuffer, tags: closeTags) {
                    let thoughtSegment = String(pendingBuffer[..<match.range.lowerBound])
                    accumulatedThinking += thoughtSegment
                    pendingBuffer.removeSubrange(..<match.range.upperBound)
                    if let first = pendingBuffer.first, first.isNewline {
                        pendingBuffer.removeFirst()
                    }
                    isCurrentlyThinking = false
                    state = .postThinkingAnswer
                    keepProcessing = true
                } else if let partialIdx = trailingPartialTagIndex(in: pendingBuffer, tags: closeTags) {
                    let safeThought = String(pendingBuffer[..<partialIdx])
                    accumulatedThinking += safeThought
                    pendingBuffer.removeSubrange(..<partialIdx)
                } else {
                    accumulatedThinking += pendingBuffer
                    pendingBuffer = ""
                }

            case .postThinkingAnswer:
                if let match = findFirstTag(in: pendingBuffer, tags: closeTags) {
                    let thoughtSegment = String(pendingBuffer[..<match.range.lowerBound])
                    accumulatedThinking += thoughtSegment
                    pendingBuffer.removeSubrange(..<match.range.upperBound)
                    if let first = pendingBuffer.first, first.isNewline {
                        pendingBuffer.removeFirst()
                    }
                    isCurrentlyThinking = false
                    keepProcessing = true
                } else {
                    accumulatedAnswer += pendingBuffer
                    pendingBuffer = ""
                }
            }
        }
    }

    private func findFirstTag(in text: String, tags: [String]) -> (tag: String, range: Range<String.Index>)? {
        var earliest: (tag: String, range: Range<String.Index>)? = nil
        for tag in tags {
            if let range = text.range(of: tag, options: .caseInsensitive) {
                if earliest == nil || range.lowerBound < earliest!.range.lowerBound {
                    earliest = (tag, range)
                }
            }
        }
        return earliest
    }

    private func trailingPartialTagIndex(in text: String, tags: [String]) -> String.Index? {
        guard let lastAngle = text.lastIndex(of: "<") else { return nil }
        let suffix = String(text[lastAngle...]).lowercased()
        for tag in tags {
            if tag.lowercased().hasPrefix(suffix) && suffix.count < tag.count {
                return lastAngle
            }
        }
        return nil
    }
}"""

    if old_start in text and old_end in text:
        idx1 = text.index(old_start)
        idx2 = text.index(old_end)
        text = text[:idx1] + new_parser + text[idx2 + len(old_end):]
        print("Replaced StatefulThinkingStreamParser successfully.")

    old_followup = "if hasThoughtOnly {\n                    var followUpMessages = apiMessages"
    new_followup = "if hasThoughtOnly {\n                    parser.transitionToPostThinkingAnswer()\n                    var followUpMessages = apiMessages"
    if old_followup in text:
        text = text.replace(old_followup, new_followup, 1)
        print("Patched hasThoughtOnly transition.")

    old_sec16 = 'rm -rf build/dmg_staging/*\nAPP_BUNDLE="build/dmg_staging/${APP_NAME}.app"'
    new_sec16 = 'APP_NAME="${APP_NAME:-AntiGravity}"\nDISPLAY_NAME="${DISPLAY_NAME:-AntiGravity}"\nBUNDLE_ID="${BUNDLE_ID:-com.antigravity.studio.macos}"\nVERSION="${VERSION:-1.0.0}"\nBUILD_NUMBER="${BUILD_NUMBER:-100}"\nrm -rf build/dmg_staging/*\nAPP_BUNDLE="build/dmg_staging/${APP_NAME}.app"'
    if old_sec16 in text:
        text = text.replace(old_sec16, new_sec16, 1)

    old_sec17 = 'ln -fsn /Applications build/dmg_staging/Applications\nDMG_NAME="${APP_NAME}-${VERSION}-macOS-arm64.dmg"'
    new_sec17 = 'APP_NAME="${APP_NAME:-AntiGravity}"\nDISPLAY_NAME="${DISPLAY_NAME:-AntiGravity}"\nVERSION="${VERSION:-1.0.0}"\nln -fsn /Applications build/dmg_staging/Applications\nDMG_NAME="${APP_NAME}-${VERSION}-macOS-arm64.dmg"'
    if old_sec17 in text:
        text = text.replace(old_sec17, new_sec17, 1)

    with open("motif_build_v12.txt", "w", encoding="utf-8") as f:
        f.write(text)
    print("motif_build_v12.txt successfully saved.")

if __name__ == "__main__":
    patch_motif()
