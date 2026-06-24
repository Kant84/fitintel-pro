// print_util.go
package main

import (
"fmt"
"os"
"os/exec"
"time"
)

func main() {
if len(os.Args) < 3 {
fmt.Println("Usage: print_util.exe <printer_name> <file_path>")
os.Exit(1)
}

printer := os.Args[1]
filePath := os.Args[2]

// Печать через notepad /p
cmd := exec.Command("notepad", "/p", filePath)
cmd.Start() // Не ждём завершения!

// Ждём 2 секунды и удаляем файл
time.Sleep(2 * time.Second)
os.Remove(filePath)

fmt.Println("OK")
}
