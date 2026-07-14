function Home() {
  return (
    <div style={{ padding: "40px" }}>
      <h1>AI Generated Courses</h1>

      <p>Generate your personalized learning path.</p>

      <input
        type="text"
        placeholder="Enter certification (e.g. AWS SAA)"
        style={{
          padding: "10px",
          width: "300px",
          marginRight: "10px"
        }}
      />

      <button>Generate</button>
    </div>
  );
}

export default Home;