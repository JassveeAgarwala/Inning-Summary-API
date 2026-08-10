from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


app = FastAPI(
    title="Khel AI Innings Summary API",
    version="1.0.0",
    description="Calculates innings statistics from raw ball-event data."
)


class Wicket(BaseModel):
    player_out: str
    kind: str
    credited_to_bowler: bool = True


class BallEvent(BaseModel):
    event_id: str
    innings_id: str
    over_number: int = Field(..., ge=0)
    ball_number: int = Field(..., ge=1)
    batter: str
    bowler: str
    batter_runs: int = Field(0, ge=0)
    extras: Dict[str, int] = {}
    wicket: Optional[Wicket] = None


class InningsSummary(BaseModel):
    innings_id: str
    total_runs: int
    wickets: int
    legal_balls: int
    overs: str
    run_rate: float
    batters: List[dict]
    bowlers: List[dict]
    top_batter: Optional[dict]
    top_bowler: Optional[dict]
    recent_balls: List[dict]


# Raw ball-event data
RAW_EVENTS = {
    "innings-001": [
        BallEvent(
            event_id="ball-1",
            innings_id="innings-001",
            over_number=0,
            ball_number=1,
            batter="Rohit Sharma",
            bowler="Mitchell Starc",
            batter_runs=4
        ),
        BallEvent(
            event_id="ball-2",
            innings_id="innings-001",
            over_number=0,
            ball_number=2,
            batter="Rohit Sharma",
            bowler="Mitchell Starc",
            batter_runs=1
        ),
        BallEvent(
            event_id="ball-3",
            innings_id="innings-001",
            over_number=0,
            ball_number=3,
            batter="Virat Kohli",
            bowler="Mitchell Starc",
            batter_runs=6
        ),
        BallEvent(
            event_id="ball-4",
            innings_id="innings-001",
            over_number=0,
            ball_number=4,
            batter="Virat Kohli",
            bowler="Mitchell Starc",
            batter_runs=0
        ),
        BallEvent(
            event_id="ball-5",
            innings_id="innings-001",
            over_number=0,
            ball_number=5,
            batter="Virat Kohli",
            bowler="Mitchell Starc",
            batter_runs=2
        ),
        BallEvent(
            event_id="ball-6",
            innings_id="innings-001",
            over_number=0,
            ball_number=6,
            batter="Virat Kohli",
            bowler="Mitchell Starc",
            batter_runs=1
        ),
        BallEvent(
            event_id="ball-7",
            innings_id="innings-001",
            over_number=1,
            ball_number=1,
            batter="Rohit Sharma",
            bowler="Pat Cummins",
            batter_runs=0,
            extras={"wides": 1}
        ),
        BallEvent(
            event_id="ball-8",
            innings_id="innings-001",
            over_number=1,
            ball_number=2,
            batter="Rohit Sharma",
            bowler="Pat Cummins",
            batter_runs=2
        ),
        BallEvent(
            event_id="ball-9",
            innings_id="innings-001",
            over_number=1,
            ball_number=3,
            batter="Rohit Sharma",
            bowler="Pat Cummins",
            batter_runs=0,
            wicket=Wicket(
                player_out="Rohit Sharma",
                kind="caught",
                credited_to_bowler=True
            )
        )
    ],
    "innings-empty": []
}


class BallEventRepository:
    def exists(self, innings_id: str) -> bool:
        return innings_id in RAW_EVENTS

    def get_events(self, innings_id: str) -> List[BallEvent]:
        return RAW_EVENTS.get(innings_id, [])


class InningsSummaryService:
    NON_BOWLER_WICKETS = {
        "run out",
        "retired hurt",
        "retired out",
        "timed out",
        "obstructing the field"
    }

    def __init__(self, repository: BallEventRepository):
        self.repository = repository

    def create_summary(
        self,
        innings_id: str
    ) -> Optional[InningsSummary]:

        if not self.repository.exists(innings_id):
            return None

        events = self.repository.get_events(innings_id)

        total_runs = sum(self.ball_total(event) for event in events)

        legal_balls = sum(
            1 for event in events
            if self.is_legal_ball(event)
        )

        wickets = sum(
            1 for event in events
            if event.wicket is not None
        )

        overs = self.format_overs(legal_balls)
        overs_decimal = legal_balls / 6

        run_rate = round(
            total_runs / overs_decimal,
            2
        ) if overs_decimal else 0.0

        batters = self.batter_summary(events)
        bowlers = self.bowler_summary(events)

        return InningsSummary(
            innings_id=innings_id,
            total_runs=total_runs,
            wickets=wickets,
            legal_balls=legal_balls,
            overs=overs,
            run_rate=run_rate,
            batters=batters,
            bowlers=bowlers,
            top_batter=self.top_batter(batters),
            top_bowler=self.top_bowler(bowlers),
            recent_balls=self.recent_balls(events)
        )

    def ball_total(self, event: BallEvent) -> int:
        return event.batter_runs + sum(event.extras.values())

    def is_legal_ball(self, event: BallEvent) -> bool:
        return (
            event.extras.get("wides", 0) == 0
            and event.extras.get("noballs", 0) == 0
        )

    def format_overs(self, legal_balls: int) -> str:
        return f"{legal_balls // 6}.{legal_balls % 6}"

    def batter_summary(self, events: List[BallEvent]) -> List[dict]:
        stats = {}

        for event in events:
            name = event.batter

            if name not in stats:
                stats[name] = {
                    "name": name,
                    "runs": 0,
                    "balls": 0,
                    "fours": 0,
                    "sixes": 0,
                    "dismissed": False
                }

            batter = stats[name]
            batter["runs"] += event.batter_runs

            if self.is_legal_ball(event):
                batter["balls"] += 1

            if event.batter_runs == 4:
                batter["fours"] += 1

            if event.batter_runs == 6:
                batter["sixes"] += 1

            if event.wicket and event.wicket.player_out == name:
                batter["dismissed"] = True

        for batter in stats.values():
            batter["strike_rate"] = round(
                (batter["runs"] / batter["balls"]) * 100,
                2
            ) if batter["balls"] else 0.0

        return list(stats.values())

    def bowler_summary(self, events: List[BallEvent]) -> List[dict]:
        stats = {}

        for event in events:
            name = event.bowler

            if name not in stats:
                stats[name] = {
                    "name": name,
                    "runs_conceded": 0,
                    "legal_balls": 0,
                    "wickets": 0
                }

            bowler = stats[name]

            bowler["runs_conceded"] += (
                event.batter_runs
                + event.extras.get("wides", 0)
                + event.extras.get("noballs", 0)
            )

            if self.is_legal_ball(event):
                bowler["legal_balls"] += 1

            if event.wicket:
                wicket_kind = event.wicket.kind.lower()

                if (
                    event.wicket.credited_to_bowler
                    and wicket_kind not in self.NON_BOWLER_WICKETS
                ):
                    bowler["wickets"] += 1

        for bowler in stats.values():
            bowler["overs"] = self.format_overs(
                bowler["legal_balls"]
            )

            overs_decimal = bowler["legal_balls"] / 6

            bowler["economy"] = round(
                bowler["runs_conceded"] / overs_decimal,
                2
            ) if overs_decimal else 0.0

        return list(stats.values())

    def top_batter(self, batters: List[dict]) -> Optional[dict]:
        if not batters:
            return None

        return max(
            batters,
            key=lambda player: (
                player["runs"],
                player["strike_rate"]
            )
        )

    def top_bowler(self, bowlers: List[dict]) -> Optional[dict]:
        if not bowlers:
            return None

        return max(
            bowlers,
            key=lambda player: (
                player["wickets"],
                -player["economy"]
            )
        )

    def recent_balls(self, events: List[BallEvent]) -> List[dict]:
        recent = []

        for event in events[-6:]:
            recent.append({
                "event_id": event.event_id,
                "over": f"{event.over_number}.{event.ball_number}",
                "batter": event.batter,
                "bowler": event.bowler,
                "runs": self.ball_total(event),
                "legal": self.is_legal_ball(event),
                "wicket": (
                    event.wicket.player_out
                    if event.wicket else None
                )
            })

        return recent


repository = BallEventRepository()
summary_service = InningsSummaryService(repository)


@app.get("/")
def home():
    return {
        "message": "Khel AI Innings Summary API is live",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.get(
    "/innings/{innings_id}/summary",
    response_model=InningsSummary
)
def get_innings_summary(innings_id: str):
    summary = summary_service.create_summary(innings_id)

    if summary is None:
        raise HTTPException(
            status_code=404,
            detail="Innings not found"
        )

    return summary
