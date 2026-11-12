package security

// Local comparison fixture, not an upstream test. No LLM or external service.
import (
	"context"
	"encoding/json"
	"os"
	"strings"
	"testing"

	"github.com/google/uuid"
	"github.com/team-memory/team-memory/internal/memory"
	"github.com/team-memory/team-memory/internal/search"
	"github.com/team-memory/team-memory/internal/testdb"
)

func TestAtlasComparison(t *testing.T) {
	var f struct {
		Source    struct{ Text string } `json:"source"`
		V1        struct{ Text string } `json:"candidate_v1"`
		V2        struct{ Text string } `json:"candidate_v2"`
		Skill     struct{ Text string } `json:"derived_skill_v1"`
		Query     string                `json:"query"`
		Forbidden []string              `json:"forbidden_markers"`
	}
	b, err := os.ReadFile(os.Getenv("ATLAS_CASE_FILE"))
	if err != nil {
		t.Fatal(err)
	}
	if err := json.Unmarshal(b, &f); err != nil {
		t.Fatal(err)
	}
	ctx := context.Background()
	d := testdb.NewDB(t)
	w := &world{t: t, db: d, svc: memory.NewService(d.App), admin: memory.NewService(d.Admin), srch: search.New(d.App, search.Config{})}
	owner := w.principal("Fixture operator", "human")
	if _, err := w.admin.CreateOrganization(ctx, owner.ID, "proyecto", "Synthetic projects"); err != nil {
		t.Fatal(err)
	}
	w.grant("proyecto", owner, memory.RoleMaintainer, true)
	if _, err := w.admin.ConfigureOrg(ctx, "proyecto", []string{"organization", "project", "personal"}, 5); err != nil {
		t.Fatal(err)
	}
	for _, sc := range []struct{ parent, level, slug string }{{"proyecto", "project", "atlas"}, {"proyecto/atlas", "personal", "ana"}, {"proyecto", "project", "boreal"}} {
		if _, err := w.admin.CreateScope(ctx, uuid.Nil, sc.parent, sc.level, sc.slug, sc.slug); err != nil {
			t.Fatal(err)
		}
	}
	ana := w.member("Ana", "proyecto/atlas/ana", memory.RoleMaintainer, false)
	bruno := w.member("Bruno", "proyecto/atlas", memory.RoleMaintainer, false)
	carla := w.member("Carla", "proyecto/boreal", memory.RoleReader, false)
	diego := w.member("Diego", "proyecto/atlas", memory.RoleReader, false)
	reader := w.member("Elena", "proyecto/atlas", memory.RoleReader, false)
	create := func(p memory.Principal, scope, title, content string) memory.Memory {
		t.Helper()
		m, e := w.svc.Create(ctx, p, memory.CreateInput{Scope: scope, Kind: string(memory.KindLesson), Title: title, Content: content})
		if e != nil {
			t.Fatal(e)
		}
		return m
	}
	find := func(p memory.Principal, id uuid.UUID) (bool, memory.Trust) {
		t.Helper()
		out, e := w.srch.Search(ctx, p, search.Input{Scope: "proyecto/atlas", Query: f.Query})
		if e != nil {
			t.Fatal(e)
		}
		for _, r := range out.Results {
			if r.ID == id {
				return true, r.Trust
			}
		}
		return false, ""
	}
	source := create(ana, "proyecto/atlas/ana", "Private synthetic session", f.Source.Text)
	candidate := create(ana, "proyecto/atlas/ana", "Webhook reintentos", f.V1.Text)
	for _, p := range []memory.Principal{bruno, carla, diego} {
		if _, e := w.svc.Get(ctx, p, source.ID, ""); !is(e, memory.ErrNotFound) {
			t.Fatalf("private source %s: %v", p.DisplayName, e)
		}
	}
	if ok, _ := find(reader, candidate.ID); ok {
		t.Fatal("private candidate leaked")
	}
	t.Log("T1/T2 private source inaccessible to Bruno/Carla/Diego; private candidate absent from Atlas reader search")
	if _, e := w.svc.Approve(ctx, portal(ana), memory.ReviewInput{ID: candidate.ID, Revision: 1}); e != nil {
		t.Fatal(e)
	}
	updated, e := w.svc.Update(ctx, ana, memory.UpdateInput{ID: candidate.ID, ExpectedRevision: 1, Content: &f.V2.Text})
	if e != nil {
		t.Fatal(e)
	}
	if updated.Trust != memory.TrustUnverified {
		t.Fatalf("trust=%s", updated.Trust)
	}
	if _, e := w.svc.Approve(ctx, portal(ana), memory.ReviewInput{ID: candidate.ID, Revision: 1}); e == nil {
		t.Fatal("stale approval accepted")
	}
	t.Log("T4 exact revision approval invalidated after edit; stale approval rejected")
	if _, e := w.svc.Update(ctx, ana, memory.UpdateInput{ID: candidate.ID, ExpectedRevision: 2, Content: &f.V1.Text}); e != nil {
		t.Fatal(e)
	}
	if _, e := w.svc.Approve(ctx, portal(ana), memory.ReviewInput{ID: candidate.ID, Revision: 3}); e != nil {
		t.Fatal(e)
	}
	req, e := w.svc.SubmitPromotion(ctx, portal(ana), memory.PromotionInput{ID: candidate.ID, Revision: 3})
	if e != nil {
		t.Fatal(e)
	}
	view, e := w.svc.GetPromotion(ctx, portal(bruno), req.ID)
	if e != nil {
		t.Fatal(e)
	}
	b, e = json.Marshal(view)
	if e != nil {
		t.Fatal(e)
	}
	for _, marker := range f.Forbidden {
		if strings.Contains(string(b), marker) {
			t.Fatalf("snapshot leaked %s", marker)
		}
	}
	if view.SourceMemoryID != nil || view.SourceScopeID != nil {
		t.Fatal("source identifiers leaked")
	}
	if _, e := w.svc.FinalizePromotion(ctx, portal(diego), req.ID, ""); !is(e, memory.ErrNotFound) {
		t.Fatalf("Diego finalize: %v", e)
	}
	if _, e := w.svc.FinalizePromotion(ctx, portal(ana), req.ID, ""); !is(e, memory.ErrForbidden) {
		t.Fatalf("Ana finalize: %v", e)
	}
	pub, e := w.svc.FinalizePromotion(ctx, portal(bruno), req.ID, "synthetic review")
	if e != nil {
		t.Fatal(e)
	}
	if ok, trust := find(reader, pub.ID); !ok || trust != memory.TrustApproved {
		t.Fatalf("approved lookup: %v %s", ok, trust)
	}
	if _, e := w.svc.Get(ctx, carla, pub.ID, ""); !is(e, memory.ErrNotFound) {
		t.Fatalf("Carla public lookup: %v", e)
	}
	t.Log("T5/T6 approved sanitized snapshot found; Bruno cannot read source; Carla excluded; Diego/Ana cannot finalize destination")
	wide, e := w.svc.SubmitPromotion(ctx, portal(bruno), memory.PromotionInput{ID: pub.ID, Revision: 1})
	if e != nil {
		t.Fatal(e)
	}
	if _, e := w.svc.FinalizePromotion(ctx, portal(bruno), wide.ID, ""); !is(e, memory.ErrForbidden) {
		t.Fatalf("org expansion by Bruno: %v", e)
	}
	if _, e := w.svc.CancelPromotion(ctx, bruno, wide.ID); e != nil {
		t.Fatal(e)
	}
	t.Log("T7 expansion Atlas -> organization requires separate destination authority")
	copyBeforeRevocation := pub.Content
	if e := w.svc.RevokeMember(ctx, bruno, "proyecto/atlas", reader.ID); e != nil {
		t.Fatal(e)
	}
	if _, e := w.svc.Get(ctx, reader, pub.ID, ""); !is(e, memory.ErrNotFound) {
		t.Fatalf("revoked reader: %v", e)
	}
	if copyBeforeRevocation != f.V1.Text {
		t.Fatal("delivered copy unexpectedly changed")
	}
	t.Log("T8 next read denied after membership revocation; already delivered in-memory copy remains")
	derived := create(bruno, "proyecto/atlas", "Webhook procedimiento derivado", f.Skill.Text)
	if _, e := w.svc.Approve(ctx, portal(bruno), memory.ReviewInput{ID: derived.ID, Revision: 1}); e != nil {
		t.Fatal(e)
	}
	if _, e := w.svc.Update(ctx, ana, memory.UpdateInput{ID: source.ID, ExpectedRevision: 1, Content: &f.V2.Text}); e != nil {
		t.Fatal(e)
	}
	unchanged, e := w.svc.Get(ctx, bruno, pub.ID, "")
	if e != nil || unchanged.Content != f.V1.Text {
		t.Fatalf("published snapshot state: %v %+v", e, unchanged)
	}
	t.Log("T9 correcting independent private source does not mutate published snapshot (no source dependency link supplied by this API)")
	if _, e := w.svc.Update(ctx, bruno, memory.UpdateInput{ID: pub.ID, ExpectedRevision: 1, Content: &f.V2.Text}); e != nil {
		t.Fatal(e)
	}
	if ok, trust := find(diego, pub.ID); !ok || trust != memory.TrustUnverified {
		t.Fatalf("edited public memory visibility: %v %s", ok, trust)
	}
	still, e := w.svc.Get(ctx, diego, derived.ID, "")
	if e != nil || still.Content != f.Skill.Text || still.Trust != memory.TrustApproved {
		t.Fatalf("derived state: %v %+v", e, still)
	}
	t.Log("OBSERVED: edited published lesson is searchable as unverified BEFORE reapproval; separately recorded derived procedure remains approved at 5 retries")
	probe := create(bruno, "proyecto/atlas", "Unapproved scope probe", f.V1.Text)
	if ok, trust := find(diego, probe.ID); !ok || trust != memory.TrustUnverified {
		t.Fatalf("same-scope draft: %v %s", ok, trust)
	}
	t.Log("OBSERVED: a new unapproved record written directly into Atlas is searchable by Atlas readers; keep proposals private until promotion")
	current, e := w.svc.Get(ctx, bruno, pub.ID, "")
	if e != nil {
		t.Fatal(e)
	}
	if _, e := w.svc.Archive(ctx, bruno, memory.ArchiveInput{ID: pub.ID, ExpectedStateVersion: current.StateVersion, Reason: "synthetic retirement"}); e != nil {
		t.Fatal(e)
	}
	if ok, _ := find(diego, pub.ID); ok {
		t.Fatal("archived lesson still in default search")
	}
	history, e := w.svc.History(ctx, diego, pub.ID)
	if e != nil || len(history.Revisions) != 2 {
		t.Fatalf("archived history: %v %+v", e, history)
	}
	if copyBeforeRevocation != f.V1.Text {
		t.Fatal("old copy unexpectedly erased")
	}
	t.Log("T10 archived lesson excluded from default search; authorized history retains two revisions; old delivered copy remains (not an export/import test)")
}
