from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class VaultWatcher:
    def __init__(self, vault_path, indexer):
        self.vault_path = vault_path
        self.indexer = indexer
    
    # Starts the watcher
    def start(self):
        observer = Observer()
        observer.schedule(VaultHandler(self.indexer), path=self.vault_path, recursive=True)
        observer.start()

        print("Watcher started successfully.")

        # Keep the watcher running until interrupted
        try:
            while True:
                pass
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

        

# A handler class for monitoring changes in the Obsidian vault directory.
class VaultHandler(FileSystemEventHandler):
    def __init__(self, indexer):
        self.indexer = indexer

    def on_modified(self, event):
        self.indexer._update_index(event)
        print(f"Modified document: {event.src_path}")

    def on_created(self, event):
        self.indexer._update_index(event, type_of_change="created")

    def on_deleted(self, event):
        self.indexer._update_index(event, type_of_change="deleted")

