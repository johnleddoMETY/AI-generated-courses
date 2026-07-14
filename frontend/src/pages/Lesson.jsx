function Lesson() {
  return (
    <div
      style={{
        maxWidth: "700px",
        margin: "50px auto",
        padding: "30px",
      }}
    >
      <h1>Identity and Access Management</h1>

      <p>
        IAM allows you to securely control access to AWS resources.
      </p>

      <h3>Topics</h3>

      <ul>
        <li>Users</li>
        <li>Groups</li>
        <li>Roles</li>
        <li>Policies</li>
      </ul>

      <button>
        Mark Lesson Complete
      </button>
    </div>
  );
}

export default Lesson;