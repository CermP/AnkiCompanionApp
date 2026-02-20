import SwiftUI
import AppKit


// MARK: - ContentView

struct ContentView: View {
    @State private var outputMessage: String = "Welcome to Anki Companion!"
    @State private var isRunning: Bool = false


    // Sélecteur de decks
    @State private var availableDecks: [String] = []
    @State private var selectedDeckIndices: Set<Int> = []
    @State private var isShowingDeckSelector = false

    var body: some View {
        VStack {
            Text("Anki Companion")
                .font(.largeTitle)
                .padding()

            if isRunning {
                ProgressView()
                    .padding()
                Text("Running script...")
            } else {
                // --- EXPORT ---
                Button("Export Decks & Media...") {
                    exportDecks()
                }
                .padding()
                .sheet(isPresented: $isShowingDeckSelector) {
                    VStack {
                        Text("Sélectionnez les decks à exporter")
                            .font(.headline)
                            .padding()

                        List {
                            ForEach(Array(availableDecks.enumerated()), id: \.offset) { index, deck in
                                HStack {
                                    Text(deck)
                                    Spacer()
                                    if selectedDeckIndices.contains(index) {
                                        Image(systemName: "checkmark.circle.fill")
                                            .foregroundColor(.blue)
                                    } else {
                                        Image(systemName: "circle")
                                            .foregroundColor(.gray)
                                    }
                                }
                                .contentShape(Rectangle())
                                .onTapGesture {
                                    if selectedDeckIndices.contains(index) {
                                        selectedDeckIndices.remove(index)
                                    } else {
                                        selectedDeckIndices.insert(index)
                                    }
                                }
                            }
                        }

                        HStack {
                            Button("Tout sélectionner") {
                                selectedDeckIndices = Set(0..<availableDecks.count)
                            }
                            Button("Tout désélectionner") {
                                selectedDeckIndices.removeAll()
                            }
                            Spacer()
                            Button("Annuler") {
                                isShowingDeckSelector = false
                            }
                            Button("Exporter") {
                                isShowingDeckSelector = false
                                proceedWithExport()
                            }
                            .buttonStyle(.borderedProminent)
                            .disabled(selectedDeckIndices.isEmpty)
                        }
                        .padding()
                    }
                    .frame(width: 500, height: 400)
                }


            }

            Divider()

            ScrollView {
                Text(outputMessage)
                    .font(.body)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding()
            }
            .frame(height: 200)
            .background(Color(.textBackgroundColor))
            .cornerRadius(8)
        }
        .padding()
        .frame(minWidth: 450, minHeight: 400)
    }


    // MARK: - Récupération des decks

    private func fetchDecks(completion: @escaping ([String]) -> Void) {
        runPythonScript(named: "list_decks.py") { success, output in
            if !success {
                self.outputMessage = "❌ Erreur lors de la récupération des decks :\n\(output)"
                completion([])
                return
            }

            let lines = output
                .split(whereSeparator: \.isNewline)
                .map(String.init)
                .filter { !$0.isEmpty }

            if let first = lines.first, first.hasPrefix("ERROR:") {
                let msg = String(first.dropFirst("ERROR:".count))
                self.outputMessage = "❌ Erreur AnkiConnect (deckNames) : \(msg)"
                completion([])
                return
            }

            completion(lines)
        }
    }


    // MARK: - Export (sans zip)

    private func exportDecks() {
        fetchDecks { decks in
            guard !decks.isEmpty else {
                return
            }

            self.availableDecks = decks
            self.selectedDeckIndices = Set(0..<decks.count)
            self.isShowingDeckSelector = true
        }
    }

    private func proceedWithExport() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.prompt = "Choisir"
        panel.message = "Choisissez le dossier où exporter les decks et médias Anki."

        panel.begin { response in
            guard response == .OK, let destinationURL = panel.url else {
                self.outputMessage = "Export annulé."
                return
            }

            let indices = self.selectedDeckIndices.sorted().map(String.init).joined(separator: ",")
            let selection = indices.isEmpty ? "all" : indices

            self.runPythonScript(
                named: "export_with_media.py",
                arguments: [destinationURL.path, selection]
            ) { success, output in
                if !success {
                    self.outputMessage = "❌ Export échoué :\n\(output)"
                    return
                }

                self.outputMessage = "✅ Export terminé dans \(destinationURL.path)\n\n\(output)"
            }
        }
    }


    // MARK: - Python

    private func findPythonExecutable() -> String? {
        let commonPaths = [
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3",
            "/Library/Frameworks/Python.framework/Versions/Current/bin/python3"
        ]

        for path in commonPaths {
            if FileManager.default.isExecutableFile(atPath: path) {
                return path
            }
        }
        return nil
    }

    private func runPythonScript(
        named scriptPath: String,
        arguments: [String] = [],
        completion: ((Bool, String) -> Void)? = nil
    ) {
        isRunning = true
        if completion == nil {
            outputMessage = "Running \(scriptPath)..."
        }

        guard let pythonPath = findPythonExecutable() else {
            self.outputMessage = "❌ Python 3 introuvable."
            self.isRunning = false
            completion?(false, outputMessage)
            return
        }

        let scriptFilename = (scriptPath as NSString).lastPathComponent
        let scriptName = scriptFilename.replacingOccurrences(of: ".py", with: "")

        // Try multiple locations: Xcode may place scripts in "scripts/" subdirectory or flat in Resources
        let scriptURL: URL
        if let url = Bundle.main.url(forResource: scriptName, withExtension: "py", subdirectory: "scripts") {
            scriptURL = url
        } else if let url = Bundle.main.url(forResource: scriptName, withExtension: "py") {
            scriptURL = url
        } else {
            // Diagnostic: list what's actually in the bundle
            var diag = "❌ Script '\(scriptFilename)' introuvable dans le bundle.\n\nContenu du bundle Resources :\n"
            if let resourcePath = Bundle.main.resourcePath {
                let fm = FileManager.default
                if let items = try? fm.contentsOfDirectory(atPath: resourcePath) {
                    for item in items.sorted() {
                        diag += "  • \(item)\n"
                        let subPath = (resourcePath as NSString).appendingPathComponent(item)
                        var isDir: ObjCBool = false
                        if fm.fileExists(atPath: subPath, isDirectory: &isDir), isDir.boolValue {
                            if let subItems = try? fm.contentsOfDirectory(atPath: subPath) {
                                for sub in subItems.sorted() {
                                    diag += "    └ \(sub)\n"
                                }
                            }
                        }
                    }
                }
            }
            self.outputMessage = diag
            isRunning = false
            completion?(false, diag)
            return
        }

        let runTask = Process()
        runTask.executableURL = URL(fileURLWithPath: pythonPath)
        runTask.arguments = [scriptURL.path] + arguments
        runTask.currentDirectoryURL = scriptURL.deletingLastPathComponent()

        let outputPipe = Pipe()
        let errorPipe = Pipe()
        runTask.standardOutput = outputPipe
        runTask.standardError = errorPipe

        runTask.terminationHandler = { process in
            DispatchQueue.main.async {
                self.isRunning = false
                let outputData = outputPipe.fileHandleForReading.readDataToEndOfFile()
                let errorData = errorPipe.fileHandleForReading.readDataToEndOfFile()
                let output = String(data: outputData, encoding: .utf8) ?? ""
                let errorOutput = String(data: errorData, encoding: .utf8) ?? ""
                let fullOutput = output + "\n" + errorOutput

                if process.terminationStatus == 0 {
                    if completion == nil {
                        self.outputMessage = "✅ Script terminé :\n\(output)"
                    }
                    completion?(true, output)
                } else {
                    if completion == nil {
                        self.outputMessage = "❌ Script échoué :\n\(fullOutput)"
                    }
                    completion?(false, fullOutput)
                }
            }
        }

        do {
            try runTask.run()
        } catch {
            self.outputMessage = "❌ Impossible de lancer le script : \(error.localizedDescription)"
            isRunning = false
            completion?(false, outputMessage)
        }
    }
}


// MARK: - Preview

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
