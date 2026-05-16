package nameentry

import "testing"

func TestAppendPrintableUpperAcceptsChris(t *testing.T) {
	got := AppendPrintableUpper("", []rune("chris"), 6)
	if got != "CHRIS" {
		t.Fatalf("got %q, want CHRIS", got)
	}
}

func TestAppendPrintableUpperKeepsMaxLength(t *testing.T) {
	got := AppendPrintableUpper("GRA", []rune("ham!"), 6)
	if got != "GRAHAM" {
		t.Fatalf("got %q, want GRAHAM", got)
	}
}
