package nameentry

import "strings"

func AppendPrintableUpper(buffer string, chars []rune, maxLen int) string {
	for _, r := range chars {
		if r < ' ' || r > '~' || len(buffer) >= maxLen {
			continue
		}
		buffer += strings.ToUpper(string(r))
	}
	return buffer
}
